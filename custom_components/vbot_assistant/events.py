"""Bridge ephemeral VBot MQTT events to the Home Assistant event bus."""

from collections import deque
import json
import logging

from homeassistant.components import mqtt
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

EVENT_VBOT = f"{DOMAIN}_event"
_LOGGER = logging.getLogger(__name__)


async def async_setup_event_bridge(hass, entry) -> None:
    """Subscribe to one device event stream with bounded deduplication."""
    runtime = entry.runtime_data
    recent_ids = deque(maxlen=256)
    recent_set = set()

    @callback
    def handle_event_on_loop(raw_payload: str) -> None:
        """Validate and forward one MQTT event from the HA event loop."""
        try:
            payload = json.loads(raw_payload)
            if not isinstance(payload, dict):
                raise ValueError("payload không phải object")
            event_type = str(payload.get("type") or "").strip().lower()
            event_id = str(payload.get("event_id") or "").strip()
            if not event_type or not event_id or event_id in recent_set:
                return
            if len(recent_ids) == recent_ids.maxlen:
                recent_set.discard(recent_ids[0])
            recent_ids.append(event_id)
            recent_set.add(event_id)

            device = dr.async_get(hass).async_get_device_by_identifier(
                (DOMAIN, runtime.device_id), entry.entry_id
            )
            event_data = {
                "device_id": device.id if device else None,
                "vbot_device_id": runtime.device_id,
                "config_entry_id": entry.entry_id,
                "type": event_type,
                "event_id": event_id,
                "timestamp": payload.get("timestamp"),
                "data": payload.get("data") if isinstance(payload.get("data"), dict) else {},
            }
            hass.bus.async_fire(EVENT_VBOT, event_data)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            _LOGGER.warning("Sự kiện MQTT VBot không hợp lệ: %s", error)

    def handle_event(message) -> None:
        """Move the MQTT callback to the Home Assistant event loop."""
        hass.add_job(handle_event_on_loop, message.payload)

    unsubscribe = await mqtt.async_subscribe(
        hass, f"{runtime.device_id}/event", handle_event, qos=1
    )
    entry.async_on_unload(unsubscribe)
