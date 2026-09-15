"""Native Home Assistant update entities for VBot."""

from __future__ import annotations

import base64
import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.components import mqtt
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .availability import MQTTAvailabilityMixin
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=12)
_METADATA_STORE = "update_metadata_store"


@dataclass(frozen=True, slots=True)
class VBotUpdateDescription:
    """Describe one independently installable VBot component."""

    key: str
    name: str
    icon: str
    installed_topic_suffix: str
    github_path: str


UPDATE_DESCRIPTIONS = (
    VBotUpdateDescription(
        key="program",
        name="Cập Nhật Chương Trình VBot",
        icon="mdi:application-import",
        installed_topic_suffix="vbot_program_version",
        github_path="Version.json",
    ),
    VBotUpdateDescription(
        key="interface",
        name="Cập Nhật Giao Diện VBot",
        icon="mdi:web-sync",
        installed_topic_suffix="vbot_interface_version",
        github_path="html/Version.json",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up update entities for one host entry."""
    runtime = entry.runtime_data
    session = async_get_clientsession(hass)
    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.setdefault(_METADATA_STORE, VBotUpdateMetadataStore(session))
    async_add_entities(
        [
            VBotUpdateEntity(hass, store, runtime.device_id, description)
            for description in UPDATE_DESCRIPTIONS
        ],
        update_before_add=True,
    )


class VBotUpdateMetadataStore:
    """Share GitHub metadata across all configured VBot devices."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def async_get(self, description: VBotUpdateDescription) -> dict[str, Any]:
        """Return cached metadata or fetch it once for all entities."""
        cached = self._cache.get(description.key)
        now = time.monotonic()
        if cached and now - cached[0] < SCAN_INTERVAL.total_seconds():
            return cached[1]

        lock = self._locks.setdefault(description.key, asyncio.Lock())
        async with lock:
            cached = self._cache.get(description.key)
            now = time.monotonic()
            if cached and now - cached[0] < SCAN_INTERVAL.total_seconds():
                return cached[1]
            url = (
                "https://api.github.com/repos/marion001/VBot_Offline/contents/"
                f"{description.github_path}"
            )
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "VBot-Update-Entity/1.0",
            }
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            async with self._session.get(url, headers=headers, timeout=timeout) as response:
                response.raise_for_status()
                payload: dict[str, Any] = await response.json()
            content = base64.b64decode(payload.get("content", ""))
            release = json.loads(content.decode("utf-8"))
            if not isinstance(release, dict):
                raise ValueError("release metadata is not an object")
            self._cache[description.key] = (time.monotonic(), release)
            return release


class VBotUpdateEntity(MQTTAvailabilityMixin, UpdateEntity):
    """Represent an installable VBot program or interface update."""

    _attr_supported_features = (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES
    )
    _attr_should_poll = True

    def __init__(
        self,
        hass: HomeAssistant,
        store: VBotUpdateMetadataStore,
        device: str,
        description: VBotUpdateDescription,
    ) -> None:
        self._hass = hass
        self._store = store
        self._device = device
        self._description = description
        self._attr_name = f"{description.name} ({device})"
        self._attr_unique_id = f"{device.lower()}_{description.key}_update"
        self._attr_icon = description.icon
        self._attr_title = description.name
        self._attr_installed_version = None
        self._attr_latest_version = None
        self._attr_release_summary = None
        self._release_notes = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        unsubscribe = await mqtt.async_subscribe(
            self._hass,
            f"{self._device}/sensor/{self._description.installed_topic_suffix}/state",
            self._handle_installed_version,
            qos=1,
        )
        self.async_on_remove(unsubscribe)

    @callback
    def _handle_installed_version(self, message) -> None:
        version = str(message.payload).strip()
        self._attr_installed_version = version or None
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Fetch the latest release metadata without doing I/O in properties."""
        try:
            release = await self._store.async_get(self._description)
            self._attr_latest_version = str(release.get("version") or "").strip() or None
            description = str(release.get("description") or "").strip()
            release_date = str(release.get("releaseDate") or "").strip()
            self._attr_release_summary = description[:255] or None
            self._release_notes = "\n\n".join(
                part for part in (description, f"Ngày phát hành: {release_date}" if release_date else "") if part
            ) or None
        except (aiohttp.ClientError, ValueError, TypeError, json.JSONDecodeError) as error:
            _LOGGER.warning(
                "Không thể kiểm tra cập nhật %s cho %s: %s",
                self._description.key,
                self._device,
                error,
            )

    async def async_install(
        self,
        version: str | None,
        backup: bool,
        **kwargs: Any,
    ) -> None:
        """Ask VBot to install the latest release."""
        await mqtt.async_publish(
            self._hass,
            f"{self._device}/script/system_update/set",
            self._description.key,
            qos=1,
            retain=False,
        )

    async def async_release_notes(self) -> str | None:
        """Return cached release notes."""
        return self._release_notes
