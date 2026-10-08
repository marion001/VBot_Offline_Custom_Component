"""Shared MQTT availability handling for VBot entities."""

import logging
import inspect
import json
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
_DEVICE_AVAILABILITY_COORDINATORS = "device_availability_coordinators"
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
        "coordinator_active": device in domain_data.get(
            _DEVICE_AVAILABILITY_COORDINATORS, {}
        ),
    }


class VBotAvailabilityCoordinator:
    """Own the three shared MQTT subscriptions for one VBot device."""

    def __init__(self, hass, device: str, runtime=None) -> None:
        self.hass = hass
        self.device = device
        self.runtime = runtime
        self._subscription_ready = False
        self._unsubscribers = []
        self._online_listeners = []
        self._update_listeners = []

    @callback
    def async_add_online_listener(self, listener):
        """Call a listener whenever this device transitions online."""
        self._online_listeners.append(listener)

        @callback
        def remove_listener() -> None:
            if listener in self._online_listeners:
                self._online_listeners.remove(listener)

        return remove_listener

    @callback
    def async_add_update_listener(self, listener):
        """Register one consumer for the shared backend OTA status."""
        self._update_listeners.append(listener)

        @callback
        def remove_listener() -> None:
            if listener in self._update_listeners:
                self._update_listeners.remove(listener)

        return remove_listener

    async def async_start(self) -> None:
        """Start the device-level subscriptions exactly once."""
        availability_topic = f"{self.device}/availability"
        self._unsubscribers.append(
            await mqtt.async_subscribe(
                self.hass,
                availability_topic,
                self._handle_availability,
                qos=1,
            )
        )
        self._unsubscribers.append(
            await mqtt.async_subscribe(
                self.hass,
                f"{self.device}/update/state",
                self._handle_update_status,
                qos=1,
            )
        )
        self._unsubscribers.append(
            await mqtt.async_subscribe(
                self.hass,
                f"{self.device}/capabilities",
                self._handle_capabilities,
                qos=1,
            )
        )

        subscribe_done = getattr(mqtt, "async_on_subscribe_done", None)
        if callable(subscribe_done):
            unsubscribe = subscribe_done(
                self.hass,
                availability_topic,
                qos=1,
                on_subscribe_status=self._handle_subscription_ready,
            )
            if inspect.isawaitable(unsubscribe):
                unsubscribe = await unsubscribe
            if callable(unsubscribe):
                self._unsubscribers.append(unsubscribe)
        else:
            self._subscription_ready = True
            self.hass.async_create_task(self._async_request_state_sync())

        subscribe_connection = getattr(
            mqtt, "async_subscribe_connection_status", None
        )
        if callable(subscribe_connection):
            unsubscribe = subscribe_connection(
                self.hass, self._handle_mqtt_connection_status
            )
            if callable(unsubscribe):
                self._unsubscribers.append(unsubscribe)

    async def async_shutdown(self) -> None:
        """Remove subscriptions owned by this coordinator."""
        while self._unsubscribers:
            unsubscribe = self._unsubscribers.pop()
            try:
                result = unsubscribe()
                if inspect.isawaitable(result):
                    await result
            except Exception as error:  # Defensive cleanup during HA shutdown.
                _LOGGER.debug(
                    "Không thể gỡ subscription availability của %s: %s",
                    self.device,
                    error,
                )
        self._subscription_ready = False
        self._online_listeners.clear()
        self._update_listeners.clear()

    @callback
    def _handle_subscription_ready(self) -> None:
        self._subscription_ready = True
        self.hass.async_create_task(self._async_request_state_sync())

    @callback
    def _handle_mqtt_connection_status(self, connected: bool) -> None:
        if not connected:
            self._subscription_ready = False
            set_vbot_device_online(self.hass, self.device, False)
            return
        if self._subscription_ready:
            self.hass.async_create_task(self._async_request_state_sync())

    @callback
    def _handle_availability(self, message) -> None:
        state = _normalize_availability(message.payload)
        if state is not None:
            was_online = is_vbot_device_online(self.hass, self.device)
            set_vbot_device_online(self.hass, self.device, state)
            if state and not was_online:
                for listener in tuple(self._online_listeners):
                    listener()

    @callback
    def _handle_capabilities(self, message) -> None:
        """Replace the last complete MQTT capability advertisement."""
        if self.runtime is None:
            return
        try:
            payload = json.loads(message.payload)
            values = payload.get("capabilities") if isinstance(payload, dict) else None
            if isinstance(values, list):
                self.runtime.set_capabilities("mqtt", values)
        except (json.JSONDecodeError, TypeError, ValueError):
            _LOGGER.debug("Payload capability không hợp lệ cho %s", self.device)

    @callback
    def _handle_update_status(self, message) -> None:
        """Parse OTA state once and fan it out to update entities."""
        try:
            payload = json.loads(message.payload)
        except (json.JSONDecodeError, TypeError, ValueError):
            return
        if not isinstance(payload, dict):
            return
        for listener in tuple(self._update_listeners):
            listener(payload)

    async def _async_request_state_sync(self) -> None:
        domain_data = self.hass.data.setdefault(DOMAIN, {})
        last_requests = domain_data.setdefault(_DEVICE_LAST_SYNC_REQUEST, {})
        now = time.monotonic()
        if now - float(last_requests.get(self.device, 0.0)) < _SYNC_REQUEST_COOLDOWN:
            return
        last_requests[self.device] = now
        domain_data.setdefault(_DEVICE_LAST_SYNC_REQUEST_WALL, {})[
            self.device
        ] = time.time()
        try:
            await mqtt.async_publish(
                self.hass,
                f"{self.device}/script/state_sync/set",
                "sync",
                qos=1,
                retain=False,
            )
        except Exception as error:
            _LOGGER.debug(
                "Chưa thể yêu cầu đồng bộ MQTT cho %s: %s", self.device, error
            )


async def async_setup_vbot_availability(hass, device: str, runtime=None) -> VBotAvailabilityCoordinator:
    """Create the single availability coordinator for a loaded entry."""
    coordinators = hass.data.setdefault(DOMAIN, {}).setdefault(
        _DEVICE_AVAILABILITY_COORDINATORS, {}
    )
    if device in coordinators:
        await coordinators[device].async_shutdown()
    coordinator = VBotAvailabilityCoordinator(hass, device, runtime)
    coordinators[device] = coordinator
    try:
        await coordinator.async_start()
    except BaseException:
        if coordinators.get(device) is coordinator:
            coordinators.pop(device, None)
        await coordinator.async_shutdown()
        raise
    return coordinator


async def async_unload_vbot_availability(hass, device: str) -> None:
    """Unload and forget one device-level coordinator."""
    coordinators = hass.data.get(DOMAIN, {}).get(
        _DEVICE_AVAILABILITY_COORDINATORS, {}
    )
    coordinator = coordinators.pop(device, None)
    if coordinator is not None:
        await coordinator.async_shutdown()


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
        _register_vbot_entity(self.hass, device, self)
        self.async_on_remove(
            lambda: _unregister_vbot_entity(self.hass, device, self)
        )
        # The availability sensor may have received the live/retained online
        # message before this platform finished adding its entities.
        if is_vbot_device_online(self.hass, device):
            self._attr_available = True
