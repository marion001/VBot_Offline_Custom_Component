"""Device automation triggers for VBot Assistant."""

from typing import Any

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_EVENT,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.helpers import device_registry as dr

from .const import CONF_DEVICE_TYPE, DEVICE_TYPE_HOST, DOMAIN
from .events import EVENT_VBOT

TRIGGER_TYPES = (
    "wake_word",
    "stt_result",
    "command_received",
    "tts_started",
    "tts_finished",
    "tts_error",
    "tts_cancelled",
    "bluetooth_connected",
    "bluetooth_disconnected",
    "multiroom_joined",
    "multiroom_left",
    "media_started",
    "media_paused",
    "media_stopped",
)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend({
    vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
})


async def async_validate_trigger_config(hass, config):
    """Validate a VBot device trigger."""
    return TRIGGER_SCHEMA(config)


async def async_get_triggers(hass, device_id: str) -> list[dict[str, Any]]:
    """Return triggers only for devices owned by this integration."""
    device = dr.async_get(hass).async_get(device_id, include_child_devices=False)
    if not device or not any(identifier[0] == DOMAIN for identifier in device.identifiers):
        return []
    entries = {
        entry.entry_id: entry for entry in hass.config_entries.async_entries(DOMAIN)
    }
    if not any(
        entries[entry_id].data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_HOST)
        == DEVICE_TYPE_HOST
        for entry_id in device.config_entries
        if entry_id in entries
    ):
        return []
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: trigger_type,
        }
        for trigger_type in TRIGGER_TYPES
    ]


async def async_attach_trigger(hass, config, action, trigger_info):
    """Attach a device trigger to the normalized VBot event bus event."""
    event_config = event_trigger.TRIGGER_SCHEMA({
        event_trigger.CONF_PLATFORM: CONF_EVENT,
        event_trigger.CONF_EVENT_TYPE: EVENT_VBOT,
        event_trigger.CONF_EVENT_DATA: {
            CONF_DEVICE_ID: config[CONF_DEVICE_ID],
            CONF_TYPE: config[CONF_TYPE],
        },
    })
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
