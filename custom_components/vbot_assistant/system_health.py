"""System health information for VBot Assistant."""

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .availability import is_vbot_device_online
from .const import DOMAIN
from .media_compat import get_media_api_compatibility


@callback
def async_register(
    hass: HomeAssistant,
    register: system_health.SystemHealthRegistration,
) -> None:
    """Register VBot system health information."""
    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict:
    """Return an aggregate, non-sensitive health summary."""
    entries = hass.config_entries.async_entries(DOMAIN)
    devices = []
    for entry in entries:
        runtime = getattr(entry, "runtime_data", None)
        if runtime is None:
            continue
        devices.append(
            {
                "device_id": runtime.device_id,
                "device_type": runtime.device_type,
                "mqtt_online": is_vbot_device_online(
                    hass, runtime.device_id
                ),
                "api_configured": bool(runtime.api_url),
                "media_api": get_media_api_compatibility(
                    hass, runtime.device_id
                ),
            }
        )
    return {
        "configured_devices": len(entries),
        "loaded_devices": len(devices),
        "online_devices": sum(
            1 for device in devices if device["mqtt_online"]
        ),
        "devices": devices,
    }
