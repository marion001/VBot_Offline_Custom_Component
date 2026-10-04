"""Native Home Assistant update entities for VBot."""

from __future__ import annotations

import base64
import asyncio
import json
import logging
import time
import weakref
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

from .availability import MQTTAvailabilityMixin, is_vbot_device_online
from .const import DOMAIN, vbot_api_headers, vbot_host_from_url

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=2)
METADATA_CACHE_TTL = timedelta(hours=12)
_METADATA_STORE = "update_metadata_store"
_UPDATE_ENTITIES = "update_entities"


def get_update_metadata_store(hass: HomeAssistant):
    """Return the integration-wide cached GitHub metadata store."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    return domain_data.setdefault(
        _METADATA_STORE,
        VBotUpdateMetadataStore(async_get_clientsession(hass)),
    )


def _format_release_version(
    release_date: str | None,
    version: str | None,
) -> str | None:
    """Format a release for Home Assistant's update dashboard."""
    normalized_version = str(version or "").strip()
    if not normalized_version:
        return None
    normalized_date = str(release_date or "").strip()
    if normalized_date:
        return f"{normalized_date} - {normalized_version}"
    return normalized_version


async def _async_get_local_release(hass, runtime, description):
    """Read installed metadata from VBot instead of stale retained MQTT."""
    host = vbot_host_from_url(runtime.api_url)
    if not host:
        raise ValueError("VBot API URL does not contain a host")
    folder = "html/" if description.key == "interface" else ""
    url = (
        f"{runtime.client.webui_base_url}/includes/php_ajax/Show_file_path.php?read_file_path"
        f"&file=/home/pi/VBot_Offline/{folder}Version.json"
    )
    timeout = aiohttp.ClientTimeout(total=15, connect=10)
    async with async_get_clientsession(hass).get(
        url, headers=vbot_api_headers(runtime.api_key), timeout=timeout
    ) as response:
        response.raise_for_status()
        payload = await response.json(content_type=None)
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise ValueError("VBot local release response is invalid")
    release = payload.get("data")
    if isinstance(release, str):
        release = json.loads(release)
    if not isinstance(release, dict):
        raise ValueError("VBot local release metadata is invalid")
    return release


async def async_refresh_vbot_updates(hass: HomeAssistant, device: str) -> None:
    """Force all native update entities for one VBot to refresh."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get(_METADATA_STORE)
    if store is not None:
        store.clear_cache()
    entities = domain_data.setdefault(_UPDATE_ENTITIES, {}).get(device, ())
    await asyncio.gather(
        *(
            entity.async_update_ha_state(force_refresh=True)
            for entity in tuple(entities)
        ),
        return_exceptions=True,
    )


@dataclass(frozen=True, slots=True)
class VBotUpdateDescription:
    """Describe one independently installable VBot component."""

    key: str
    name: str
    icon: str
    installed_topic_suffix: str
    installed_release_date_topic_suffix: str
    github_path: str


UPDATE_DESCRIPTIONS = (
    VBotUpdateDescription(
        key="program",
        name="Cập Nhật Chương Trình VBot",
        icon="mdi:application-import",
        installed_topic_suffix="vbot_program_version",
        installed_release_date_topic_suffix="vbot_program_releaseDate",
        github_path="Version.json",
    ),
    VBotUpdateDescription(
        key="interface",
        name="Cập Nhật Giao Diện VBot",
        icon="mdi:web-sync",
        installed_topic_suffix="vbot_interface_version",
        installed_release_date_topic_suffix="vbot_interface_releaseDate",
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
    store = get_update_metadata_store(hass)
    async_add_entities(
        [
            VBotUpdateEntity(
                hass,
                store,
                runtime.device_id,
                description,
                runtime.availability_coordinator,
                runtime,
            )
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

    def clear_cache(self) -> None:
        """Discard cached GitHub metadata for a manual refresh."""
        self._cache.clear()

    async def async_get(self, description: VBotUpdateDescription) -> dict[str, Any]:
        """Return cached metadata or fetch it once for all entities."""
        cached = self._cache.get(description.key)
        now = time.monotonic()
        if cached and now - cached[0] < METADATA_CACHE_TTL.total_seconds():
            return cached[1]

        lock = self._locks.setdefault(description.key, asyncio.Lock())
        async with lock:
            cached = self._cache.get(description.key)
            now = time.monotonic()
            if cached and now - cached[0] < METADATA_CACHE_TTL.total_seconds():
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
        coordinator,
        runtime,
    ) -> None:
        self._hass = hass
        self._store = store
        self._device = device
        self._description = description
        self._coordinator = coordinator
        self._runtime = runtime
        self._attr_name = f"{description.name} ({device})"
        self._attr_unique_id = f"{device.lower()}_{description.key}_update"
        self._attr_icon = description.icon
        self._attr_title = description.name
        # Update checks require an explicit retained MQTT "online" message.
        self._attr_available = False
        self._attr_installed_version = None
        self._attr_latest_version = None
        self._installed_version_number = None
        self._installed_release_date = None
        self._attr_release_summary = None
        self._release_notes = None
        self._update_status = None
        self._local_refresh_pending = False
        self._local_refresh_task = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        entities = self.hass.data.setdefault(DOMAIN, {}).setdefault(
            _UPDATE_ENTITIES, {}
        ).setdefault(self._device, weakref.WeakSet())
        entities.add(self)
        self.async_on_remove(lambda: entities.discard(self))
        unsubscribe = await mqtt.async_subscribe(
            self._hass,
            f"{self._device}/sensor/{self._description.installed_topic_suffix}/state",
            self._handle_installed_version,
            qos=1,
        )
        self.async_on_remove(unsubscribe)
        unsubscribe_release_date = await mqtt.async_subscribe(
            self._hass,
            f"{self._device}/sensor/{self._description.installed_release_date_topic_suffix}/state",
            self._handle_installed_release_date,
            qos=1,
        )
        self.async_on_remove(unsubscribe_release_date)
        self.async_on_remove(
            self._coordinator.async_add_update_listener(
                self._handle_update_status
            )
        )

    @callback
    def _handle_update_status(self, payload) -> None:
        """Expose backend OTA lifecycle and completion state."""
        target = str(payload.get("target") or "").strip()
        if target and target != self._description.key:
            return
        self._update_status = payload
        self._attr_in_progress = bool(payload.get("running"))
        self.async_write_ha_state()
        if not self._attr_in_progress and str(payload.get("status") or "").lower() in {
            "success", "completed", "complete", "updated",
        }:
            self._hass.async_create_task(
                self.async_update_ha_state(force_refresh=True)
            )

    @property
    def extra_state_attributes(self):
        """Return the latest non-sensitive backend update status."""
        if not self._update_status:
            return None
        return {
            "update_status": self._update_status.get("status"),
            "update_message": self._update_status.get("message"),
            "update_started_at": self._update_status.get("started_at"),
            "update_finished_at": self._update_status.get("finished_at"),
        }

    def _refresh_installed_version(self) -> None:
        """Expose local release date and version as one HA update value."""
        self._attr_installed_version = _format_release_version(
            self._installed_release_date,
            self._installed_version_number,
        )

    def _schedule_local_release_refresh(self) -> None:
        """Replace retained MQTT metadata with the current Version.json values."""
        if self._local_refresh_pending:
            return
        self._local_refresh_pending = True

        async def refresh_after_retained_messages():
            try:
                await asyncio.sleep(1)
                await self.async_update_ha_state(force_refresh=True)
            finally:
                self._local_refresh_pending = False
                self._local_refresh_task = None

        self._local_refresh_task = self._hass.async_create_task(refresh_after_retained_messages())

    async def async_will_remove_from_hass(self) -> None:
        task = self._local_refresh_task
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                self._local_refresh_task = None
                self._local_refresh_pending = False
        await super().async_will_remove_from_hass()

    @callback
    def _handle_installed_version(self, message) -> None:
        version = str(message.payload).strip()
        self._installed_version_number = version or None
        self._refresh_installed_version()
        self.async_write_ha_state()
        self._schedule_local_release_refresh()

    @callback
    def _handle_installed_release_date(self, message) -> None:
        release_date = str(message.payload).strip()
        self._installed_release_date = release_date or None
        self._refresh_installed_version()
        self.async_write_ha_state()
        self._schedule_local_release_refresh()

    async def async_update(self) -> None:
        """Fetch the latest release metadata without doing I/O in properties."""
        if not is_vbot_device_online(self._hass, self._device):
            _LOGGER.debug(
                "Bỏ qua kiểm tra cập nhật %s cho %s vì thiết bị offline",
                self._description.key,
                self._device,
            )
            return
        try:
            local_result, release_result = await asyncio.gather(
                _async_get_local_release(self._hass, self._runtime, self._description),
                self._store.async_get(self._description),
                return_exceptions=True,
            )
            if isinstance(local_result, dict):
                self._installed_version_number = str(local_result.get("version") or "").strip() or None
                self._installed_release_date = str(
                    local_result.get("releaseDate") or local_result.get("release_date") or ""
                ).strip() or None
                self._refresh_installed_version()
            elif isinstance(local_result, Exception):
                _LOGGER.warning(
                    "Không thể đọc phiên bản cài đặt %s cho %s: %s",
                    self._description.key, self._device, local_result,
                )
            if isinstance(release_result, Exception):
                raise release_result
            release = release_result
            latest_version = str(release.get("version") or "").strip()
            description = str(release.get("description") or "").strip()
            release_date = str(release.get("releaseDate") or "").strip()
            self._attr_latest_version = _format_release_version(
                release_date,
                latest_version,
            )
            self._attr_release_summary = description[:255] or None
            self._release_notes = "\n\n".join(
                part for part in (description, f"Ngày phát hành: {release_date}" if release_date else "") if part
            ) or None
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError, json.JSONDecodeError) as error:
            _LOGGER.warning(
                "Không thể kiểm tra cập nhật %s cho %s: %s",
                self._description.key,
                self._device,
                error,
            )

    def version_is_newer(
        self,
        latest_version: str,
        installed_version: str,
    ) -> bool:
        """Treat any different release metadata as an available update.

        Both values use ``releaseDate - version``. VBot release dates are the
        authoritative build identifiers, so equality is the only state that
        means the installed build is current.
        """
        return str(latest_version).strip() != str(installed_version).strip()

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
            json.dumps({
                "target": self._description.key,
                "backup_before_update": bool(backup),
            }),
            qos=1,
            retain=False,
        )

    async def async_release_notes(self) -> str | None:
        """Return cached release notes."""
        return self._release_notes
