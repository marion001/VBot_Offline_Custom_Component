"""Per-entry runtime state for VBot Assistant."""

from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VBotApiClient
from .const import CONF_API_KEY, CONF_CAPABILITIES, CONF_DEVICE_ID, CONF_DEVICE_TYPE, DEVICE_TYPE_HOST, VBot_URL_API, normalize_vbot_url


@dataclass(slots=True)
class VBotRuntimeData:
    """Configuration and clients owned by exactly one config entry."""

    entry_id: str
    device_id: str
    device_type: str
    api_url: str
    api_key: str
    client: VBotApiClient
    capabilities: set[str] = field(default_factory=set)
    media_api_version: int | None = None
    availability_coordinator: Any | None = None
    mdns_capabilities: set[str] = field(default_factory=set)
    mqtt_capabilities: set[str] | None = None
    media_capabilities: set[str] | None = None
    media_capability_scope: set[str] = field(default_factory=set)
    configuration: dict = field(default_factory=dict)

    def set_capabilities(self, source: str, values, *, scope=()) -> None:
        """Replace one advertisement; MQTT overrides discovery, Media API owns its scope."""
        if not isinstance(values, (list, tuple, set)):
            return
        setattr(self, f"{source}_capabilities", {
            value.strip() for value in values if isinstance(value, str) and value.strip()
        })
        if source == "media":
            self.media_capability_scope.update(scope)
            self.media_capability_scope.update(self.media_capabilities)
        effective = set(self.mdns_capabilities if self.mqtt_capabilities is None else self.mqtt_capabilities)
        if self.media_capabilities is not None:
            effective.difference_update(self.media_capability_scope)
            effective.update(self.media_capabilities)
        self.capabilities = effective

    def accept_metadata_update(self, entry) -> bool:
        """Skip reload for discovery metadata alone, keeping active conversations intact."""
        from .const import CONF_MDNS_LAST_UPDATE
        current = {
            "data": {key: value for key, value in entry.data.items()
                     if key not in {CONF_CAPABILITIES, "name", "version"}},
            "options": {key: value for key, value in entry.options.items()
                        if key != CONF_MDNS_LAST_UPDATE},
        }
        unchanged = current == self.configuration
        self.configuration = current
        self.set_capabilities("mdns", entry.data.get(CONF_CAPABILITIES, []))
        return unchanged


def build_runtime_data(hass: HomeAssistant, entry: ConfigEntry) -> VBotRuntimeData:
    """Build fresh runtime data after setup or an options reload."""
    device_type = entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_HOST)
    api_url = normalize_vbot_url(entry.data.get(VBot_URL_API, ""), device_type)
    api_key = str(entry.data.get(CONF_API_KEY, "")).strip()
    runtime = VBotRuntimeData(
        entry_id=entry.entry_id,
        device_id=str(entry.data.get(CONF_DEVICE_ID, "")).strip(),
        device_type=device_type,
        api_url=api_url,
        api_key=api_key,
        client=VBotApiClient(async_get_clientsession(hass), api_url, api_key),
    )
    runtime.accept_metadata_update(entry)
    return runtime
