"""Shared MQTT availability handling for VBot entities."""

import logging
import inspect
import time
import weakref

from homeassistant.components import mqtt
from homeassistant.core import callback

from .const import DOMAIN
from .entity import VBotEntity


_LOGGER = logging.getLogger(__name__)
_DEVICE_AVAILABILITY = "device_availability"
_DEVICE_AVAILABILITY_ENTITIES = "device_availability_entities"
_DEVICE_LAST_SYNC_REQUEST = "device_last_sync_request"
_DEVICE_AVAILABILITY_CHANGED = "device_availability_changed"
_DEVICE_LAST_SYNC_REQUEST_WALL = "device_last_sync_request_wall"
_SYNC_REQUEST_COOLDOWN = 5.0


def _normalize_availability(payload) -> bool | None:
    """Convert MQTT availability payloads to online/offline/unknown."""
    value = str(payload or "").strip().lower()
    if value in {"online", "connected", "ready"}:
        return True
    if value in {"offline", "unavailable", "disconnected", "lost"}:
        return False
    return None


def set_vbot_device_online(hass, device: str, online: bool) -> None:
    """Store and fan out explicit availability to every entity of a VBot."""
    if not device:
        return
    domain_data = hass.data.setdefault(DOMAIN, {})
    state = bool(online)
    states = domain_data.setdefault(_DEVICE_AVAILABILITY, {})
    if states.get(device) != state:
        domain_data.setdefault(_DEVICE_AVAILABILITY_CHANGED, {})[device] = time.time()
    states[device] = state
    entities = domain_data.setdefault(_DEVICE_AVAILABILITY_ENTITIES, {}).get(device, ())
    for entity in tuple(entities):
        if getattr(entity, "_vbot_availability_exempt", False):
            continue
        changed = getattr(entity, "_attr_available", None) != state
        entity._attr_available = state
        if changed and getattr(entity, "hass", None) is not None:
            # Coalesce the reconnect burst instead of synchronously writing
            # dozens of entity states inside one MQTT callback.
            schedule_update = getattr(
                entity, "async_schedule_update_ha_state", None
            )
            if callable(schedule_update):
                schedule_update()
            else:  # Lightweight test doubles and older HA compatibility.
                entity.async_write_ha_state()


def _register_vbot_entity(hass, device: str, entity) -> None:
    """Register an entity for device-wide availability updates."""
    entities = hass.data.setdefault(DOMAIN, {}).setdefault(
        _DEVICE_AVAILABILITY_ENTITIES, {}
    ).setdefault(device, weakref.WeakSet())
    entities.add(entity)


def _unregister_vbot_entity(hass, device: str, entity) -> None:
    """Remove an entity from device-wide availability updates."""
    device_entities = hass.data.get(DOMAIN, {}).get(
        _DEVICE_AVAILABILITY_ENTITIES, {}
    ).get(device)
    if device_entities is not None:
        device_entities.discard(entity)


def is_vbot_device_online(hass, device: str) -> bool:
    """Return True only after a positive MQTT availability signal."""
    return hass.data.get(DOMAIN, {}).get(
        _DEVICE_AVAILABILITY, {}
    ).get(device) is True


def reset_vbot_device_availability(hass, device: str) -> None:
    """Clear stale online/sync state across entry reloads and unloads."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault(_DEVICE_AVAILABILITY, {})[device] = False
    domain_data.setdefault(_DEVICE_LAST_SYNC_REQUEST, {}).pop(device, None)


def get_vbot_availability_diagnostics(hass, device: str) -> dict:
    """Return non-sensitive MQTT availability diagnostics for one device."""
    domain_data = hass.data.get(DOMAIN, {})
    return {
        "online": is_vbot_device_online(hass, device),
        "availability_changed_at": domain_data.get(
            _DEVICE_AVAILABILITY_CHANGED, {}
        ).get(device),
        "last_state_sync_request_at": domain_data.get(
            _DEVICE_LAST_SYNC_REQUEST_WALL, {}
        ).get(device),
        "registered_entity_count": len(
            domain_data.get(_DEVICE_AVAILABILITY_ENTITIES, {}).get(device, ())
        ),
    }


class MQTTAvailabilityMixin(VBotEntity):
    """Combine HA MQTT connectivity with the VBot retained/LWT status."""

    _attr_available = False

    @property
    def available(self) -> bool:
        """Read availability from the device-wide source of truth.

        Do not let a stale per-entity ``_attr_available`` keep controls
        unavailable after another subscriber has received VBot's online
        message.
        """
        if getattr(self, "_vbot_availability_exempt", False):
            return True
        device = getattr(self, "_device", None)
        if not device or getattr(self, "hass", None) is None:
            return False
        return is_vbot_device_online(self.hass, device)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if getattr(self, "_vbot_availability_exempt", False):
            self._attr_available = True
            return
        device = getattr(self, "_device", None)
        if not device:
            return

        self._attr_available = False
        self._availability_subscription_ready = False
        _register_vbot_entity(self.hass, device, self)
        self.async_on_remove(
            lambda: _unregister_vbot_entity(self.hass, device, self)
        )
        # The availability sensor may have received the live/retained online
        # message before this platform finished adding its entities.
        if is_vbot_device_online(self.hass, device):
            self._attr_available = True
        availability_topic = f"{device}/availability"
        unsubscribe = await mqtt.async_subscribe(
            self.hass,
            availability_topic,
            self._handle_vbot_availability,
            qos=1,
        )
        self.async_on_remove(unsubscribe)

        subscribe_done = getattr(mqtt, "async_on_subscribe_done", None)
        if callable(subscribe_done):
            unsubscribe_done = subscribe_done(
                self.hass,
                availability_topic,
                qos=1,
                on_subscribe_status=self._handle_availability_subscription_ready,
            )
            # Current HA returns the unsubscribe callback directly. Retain
            # compatibility in case an older/newer release returns an awaitable.
            if inspect.isawaitable(unsubscribe_done):
                unsubscribe_done = await unsubscribe_done
            self.async_on_remove(unsubscribe_done)
        else:
            # Compatibility fallback for HA releases before this helper existed.
            self._availability_subscription_ready = True
            self.hass.async_create_task(self._async_request_state_sync())

        subscribe_connection = getattr(mqtt, "async_subscribe_connection_status", None)
        if callable(subscribe_connection):
            unsubscribe_connection = subscribe_connection(
                self.hass, self._handle_mqtt_connection_status
            )
            if callable(unsubscribe_connection):
                self.async_on_remove(unsubscribe_connection)


    @callback
    def _handle_availability_subscription_ready(self) -> None:
        """Request state only after the broker acknowledged our subscription."""
        self._availability_subscription_ready = True
        if is_vbot_device_online(self.hass, self._device):
            set_vbot_device_online(self.hass, self._device, True)
        self.hass.async_create_task(self._async_request_state_sync())

    @callback
    def _handle_mqtt_connection_status(self, connected: bool) -> None:
        """Make controls unavailable while Home Assistant has no MQTT link."""
        device = getattr(self, "_device", None)
        if connected:
            # A broker reconnect is not an offline signal from this VBot. Keep
            # any explicit online state already received and request a refresh.
            if is_vbot_device_online(self.hass, device):
                set_vbot_device_online(self.hass, device, True)
            if self._availability_subscription_ready:
                self.hass.async_create_task(self._async_request_state_sync())
        else:
            changed = getattr(self, "_attr_available", None) is not False
            self._attr_available = False
            set_vbot_device_online(self.hass, device, False)
            if changed:
                self.async_write_ha_state()
            self._availability_subscription_ready = False

    async def _async_request_state_sync(self) -> None:
        """Ask one VBot to republish availability and all retained states."""
        device = getattr(self, "_device", None)
        if not device:
            return
        domain_data = self.hass.data.setdefault(DOMAIN, {})
        last_requests = domain_data.setdefault(_DEVICE_LAST_SYNC_REQUEST, {})
        now = time.monotonic()
        if now - float(last_requests.get(device, 0.0)) < _SYNC_REQUEST_COOLDOWN:
            return
        last_requests[device] = now
        domain_data.setdefault(_DEVICE_LAST_SYNC_REQUEST_WALL, {})[
            device
        ] = time.time()
        try:
            await mqtt.async_publish(
                self.hass,
                f"{device}/script/state_sync/set",
                "sync",
                qos=1,
                retain=False,
            )
        except Exception as error:  # MQTT reconnect can race entity setup.
            _LOGGER.debug("Chưa thể yêu cầu đồng bộ MQTT cho %s: %s", device, error)

    @callback
    def _handle_vbot_availability(self, message) -> None:
        """Apply only explicit online/offline messages from this VBot."""
        state = _normalize_availability(message.payload)
        if state is None:
            return
        changed = getattr(self, "_attr_available", None) != state
        self._attr_available = state
        set_vbot_device_online(self.hass, self._device, state)
        if changed:
            self.async_write_ha_state()
