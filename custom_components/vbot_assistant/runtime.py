"""Per-entry runtime state for VBot Assistant."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VBotApiClient
from .const import CONF_API_KEY, CONF_DEVICE_ID, CONF_DEVICE_TYPE, DEVICE_TYPE_HOST, VBot_URL_API, normalize_vbot_url


@dataclass(slots=True)
class VBotRuntimeData:
    """Configuration and clients owned by exactly one config entry."""

    entry_id: str
    device_id: str
    device_type: str
    api_url: str
    api_key: str
    client: VBotApiClient


def build_runtime_data(hass: HomeAssistant, entry: ConfigEntry) -> VBotRuntimeData:
    """Build fresh runtime data after setup or an options reload."""
    device_type = entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_HOST)
    api_url = normalize_vbot_url(entry.data.get(VBot_URL_API, ""), device_type)
    api_key = str(entry.data.get(CONF_API_KEY, "")).strip()
    return VBotRuntimeData(
        entry_id=entry.entry_id,
        device_id=str(entry.data.get(CONF_DEVICE_ID, "")).strip(),
        device_type=device_type,
        api_url=api_url,
        api_key=api_key,
        client=VBotApiClient(async_get_clientsession(hass), api_url, api_key),
    )
