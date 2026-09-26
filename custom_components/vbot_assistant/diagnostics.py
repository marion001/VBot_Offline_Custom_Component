"""Diagnostics support for VBot Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .availability import get_vbot_availability_diagnostics
from .const import CONF_API_KEY, DOMAIN
from .media_compat import get_media_api_compatibility


TO_REDACT = {CONF_API_KEY, "password", "token", "mqtt_password"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return safe diagnostics for one VBot config entry."""
    runtime = entry.runtime_data
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
            "device_id": runtime.device_id,
            "device_type": runtime.device_type,
            "api_url": runtime.api_url,
            "api_key_configured": bool(runtime.api_key),
            "capabilities": sorted(runtime.capabilities),
            "media_api_version": runtime.media_api_version,
        },
        "mqtt": get_vbot_availability_diagnostics(
            hass, runtime.device_id
        ),
        "media_api": get_media_api_compatibility(hass, runtime.device_id),
    }
