"""Diagnostics support for VBot Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .availability import get_vbot_availability_diagnostics
from .const import CONF_API_KEY, CONF_DEVICE_ID, DOMAIN
from .media_compat import get_media_api_compatibility


TO_REDACT = {CONF_API_KEY, "password", "token", "mqtt_password"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return safe diagnostics for one VBot config entry."""
    runtime = getattr(entry, "runtime_data", None)
    device_id = getattr(runtime, "device_id", entry.data.get(CONF_DEVICE_ID, ""))
    return {
        "integration": {
            "domain": DOMAIN,
            "entry_id": entry.entry_id,
            "title": entry.title,
            "version": entry.version,
        },
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "entry_options": async_redact_data(dict(entry.options), TO_REDACT),
        "runtime": {
            "loaded": runtime is not None,
            "device_id": device_id,
            "device_type": getattr(runtime, "device_type", None),
            "api_url": getattr(runtime, "api_url", None),
            "api_key_configured": bool(getattr(runtime, "api_key", entry.data.get(CONF_API_KEY, ""))),
            "capabilities": sorted(getattr(runtime, "capabilities", [])),
            "media_api_version": getattr(runtime, "media_api_version", None),
        },
        "mqtt": get_vbot_availability_diagnostics(
            hass, device_id
        ),
        "media_api": get_media_api_compatibility(hass, device_id),
    }
