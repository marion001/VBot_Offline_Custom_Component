'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

from __future__ import annotations

import logging
import math
import json
from pathlib import Path
from typing import TYPE_CHECKING
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit
import posixpath
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er
from .const import (
    DOMAIN, CONF_DEVICE_ID, VBot_URL_API,
    CONF_DEVICE_TYPE, DEVICE_TYPE_ANDROID, DEVICE_TYPE_ESP32, DEVICE_TYPE_HOST,
)
from .availability import MQTTAvailabilityMixin

if TYPE_CHECKING:
    from homeassistant.components.media_player import BrowseMedia, SearchMedia, SearchMediaQuery

_LOGGER = logging.getLogger(__name__)
_LOCAL_LOGO_PATH = Path(__file__).with_name("logo.png")
_LOCAL_LOGO_URL = "vbot-assistant://logo.png"

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    runtime = entry.runtime_data
    device = runtime.device_id
    if not device:
        _LOGGER.error("Không tìm thấy device_id trong cấu hình")
        return

    api_url = runtime.api_url
    use_host_default_cover = runtime.device_type == DEVICE_TYPE_HOST
    esp32_profile = runtime.device_type == DEVICE_TYPE_ESP32
    async_add_entities([
        VBotMediaPlayer(
            hass, device, api_url, use_host_default_cover, esp32_profile, entry.entry_id
        )
    ])

class VBotMediaPlayer(MQTTAvailabilityMixin, MediaPlayerEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        device: str,
        api_url: str = "",
        use_host_default_cover: bool = False,
        esp32_profile: bool = False,
        entry_id: str = "",
    ):
        self._hass = hass
        self._device = device
        self._entry_id = entry_id
        self._attr_name = f"Media Player ({device})"
        self._attr_unique_id = f"{device.lower()}_media_player"
        self._attr_state = MediaPlayerState.IDLE
        self._attr_supported_features = (
            MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.VOLUME_SET
            if esp32_profile else
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.SEEK
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
        )
        if use_host_default_cover:
            self._attr_supported_features |= (
                MediaPlayerEntityFeature.GROUPING
                | MediaPlayerEntityFeature.BROWSE_MEDIA
                | MediaPlayerEntityFeature.SEARCH_MEDIA
            )
        self._media_title = None
        self._media_url = None
        self._attr_available = False
        self._attr_source = None
        self._attr_media_artist = None
        self._attr_media_album_name = None
        self._attr_media_duration = None
        self._attr_media_position = None
        self._attr_media_position_updated_at = None
        self._attr_media_image_url = None
        self._attr_volume_level = None
        self._source_kind = None
        self._multiroom = {}
        self._is_host_device = use_host_default_cover
        self._default_cover_url = _LOCAL_LOGO_URL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        unsubscribe = await mqtt.async_subscribe(
            self._hass,
            f"{self._device}/media_player/state",
            self._handle_state_message,
            qos=1,
        )
        self.async_on_remove(unsubscribe)
        unsubscribe_multiroom = await mqtt.async_subscribe(
            self._hass, f"{self._device}/multiroom/state",
            self._handle_multiroom_message, qos=1,
        )
        self.async_on_remove(unsubscribe_multiroom)

    @callback
    def _handle_multiroom_message(self, message) -> None:
        try:
            payload = json.loads(message.payload)
            if isinstance(payload, dict):
                self._multiroom = payload
                self._attr_group_members = self._group_entity_ids(payload)
                if payload.get("has_media"):
                    title = payload.get("title")
                    cover = str(payload.get("cover") or "").strip()
                    duration = self._number_or_none(payload.get("duration_ms"))
                    if title:
                        self._media_title = title
                    if cover:
                        self._attr_media_image_url = cover
                    elif title:
                        self._attr_media_image_url = self._default_cover_url
                    if duration is not None:
                        self._attr_media_duration = duration
                self.async_write_ha_state()
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            _LOGGER.warning("Snapshot Multiroom VBot không hợp lệ: %s", error)

    def _entity_id_for_device(self, device_id: str):
        registry = er.async_get(self._hass)
        return registry.async_get_entity_id(
            "media_player", DOMAIN, f"{device_id.lower()}_media_player"
        )

    def _group_entity_ids(self, payload):
        """Map backend speaker IDs to registered Home Assistant entities."""
        members = []
        if payload.get("coordinator") and self.entity_id:
            members.append(self.entity_id)
        # HA entity unique IDs are based on MQTT Client ID. New backends publish
        # both forms; speaker_ids remains as a compatibility fallback.
        speaker_ids = payload.get("speaker_mqtt_ids") or payload.get("speaker_ids") or []
        for speaker_id in speaker_ids:
            entity_id = self._entity_id_for_device(str(speaker_id))
            if entity_id and entity_id not in members:
                members.append(entity_id)
        coordinator_name = str(payload.get("coordinator_name") or "").strip()
        if not members and coordinator_name:
            entity_id = self._entity_id_for_device(coordinator_name)
            if entity_id:
                members.extend([entity_id, self.entity_id])
        return members or None

    def _devices_from_entity_ids(self, entity_ids):
        """Resolve media-player entity IDs without depending on their display names."""
        registry = er.async_get(self._hass)
        requested = set(entity_ids)
        devices = []
        for entry in self._hass.config_entries.async_entries(DOMAIN):
            runtime = getattr(entry, "runtime_data", None)
            if not runtime or not runtime.device_id:
                continue
            entity_id = registry.async_get_entity_id(
                "media_player", DOMAIN,
                f"{runtime.device_id.lower()}_media_player",
            )
            if entity_id in requested and runtime.device_id != self._device:
                devices.append(runtime.device_id.lower())
        return list(dict.fromkeys(devices))

    def _coordinator_device(self):
        """Resolve coordinator metadata to the configured MQTT client ID."""
        coordinator_name = str(
            self._multiroom.get("coordinator_name") or ""
        ).strip()
        coordinator_host = str(
            self._multiroom.get("coordinator_host") or ""
        ).strip().lower()
        for entry in self._hass.config_entries.async_entries(DOMAIN):
            runtime = getattr(entry, "runtime_data", None)
            if not runtime:
                continue
            if coordinator_name and runtime.device_id.lower() == coordinator_name.lower():
                return runtime.device_id
            runtime_host = (urlsplit(runtime.api_url).hostname or "").lower()
            if coordinator_host and runtime_host == coordinator_host:
                return runtime.device_id
        return coordinator_name or None

    async def async_join_players(self, group_members: list[str]) -> None:
        """Create and start a VBot Multiroom group from HA media players."""
        remote_speaker_ids = self._devices_from_entity_ids(group_members)
        if not remote_speaker_ids:
            requested = {
                str(entity_id or "").strip()
                for entity_id in (group_members or [])
                if str(entity_id or "").strip()
            }
            # HA uses join with an empty/self-only member list when the user
            # reduces a group back to its coordinator. Treat that as unjoin.
            if not requested or requested == {self.entity_id}:
                if self._multiroom.get("connected") or self._multiroom.get("coordinator"):
                    await self.async_unjoin_player()
                return
            raise ValueError("Không tìm thấy loa VBot hợp lệ để ghép nhóm")
        # HA treats this entity as coordinator. Include it in the network
        # stream because local ALSA passthrough stops while capture is active.
        speaker_ids = list(dict.fromkeys([
            self._device.lower(), *remote_speaker_ids
        ]))
        payload = {
            "action": "join",
            "group_id": f"home_assistant_{self._device.lower()}",
            "speaker_ids": speaker_ids,
        }
        await mqtt.async_publish(
            self._hass,
            f"{self._device}/script/multiroom_control/set",
            json.dumps(payload), qos=1, retain=False,
        )

    async def async_unjoin_player(self) -> None:
        """Stop a coordinator group or remove this player from its coordinator."""
        if self._multiroom.get("coordinator"):
            target_device = self._device
            payload = {"action": "stop"}
        else:
            target_device = self._coordinator_device()
            if not target_device:
                raise ValueError("Không xác định được coordinator Multiroom")
            payload = {
                "action": "remove_speakers",
                "speaker_ids": [self._device.lower()],
            }
        await mqtt.async_publish(
            self._hass,
            f"{target_device}/script/multiroom_control/set",
            json.dumps(payload), qos=1, retain=False,
        )

    @callback
    def _handle_state_message(self, message) -> None:
        try:
            payload = json.loads(message.payload)
            if not isinstance(payload, dict):
                raise ValueError("payload không phải object")
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            _LOGGER.warning("Snapshot Media Player VBot không hợp lệ: %s", error)
            return

        state = str(payload.get("state", "idle")).lower()
        if state == "unavailable":
            # Media playback state is not MQTT device availability. The VBot
            # LWT topic is the only source allowed to take every control
            # offline; otherwise one stale media snapshot disables all entities.
            self._attr_state = MediaPlayerState.IDLE
            self.async_write_ha_state()
            return

        state_mapping = {
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
            "idle": MediaPlayerState.IDLE,
        }
        self._attr_state = state_mapping.get(state, MediaPlayerState.IDLE)
        previous_title = self._media_title
        previous_source_kind = self._source_kind
        incoming_title = payload.get("title")
        incoming_source_kind = payload.get("source_kind")
        same_media = bool(
            incoming_title and previous_title
            and str(incoming_title) == str(previous_title)
            and incoming_source_kind == previous_source_kind
        )
        self._media_title = incoming_title
        self._attr_media_artist = payload.get("artist")
        self._attr_media_album_name = payload.get("album")
        self._media_url = payload.get("media_url")
        cover = str(payload.get("cover") or "").strip()
        active_state = self._attr_state in (MediaPlayerState.PLAYING, MediaPlayerState.PAUSED)
        if cover:
            self._attr_media_image_url = cover
        elif not active_state:
            self._attr_media_image_url = None
        elif not same_media:
            self._attr_media_image_url = self._default_cover_url
        self._attr_source = payload.get("source")
        self._source_kind = incoming_source_kind
        self._playlist_active = bool(payload.get("playlist_active"))
        self._playlist_id = payload.get("playlist_id")
        self._playlist_name = payload.get("playlist_name")
        self._playlist_index = payload.get("playlist_index")
        self._playlist_total = payload.get("playlist_total", 0)
        self._playlist_loop = bool(payload.get("playlist_loop"))
        incoming_duration = self._number_or_none(payload.get("duration"))
        incoming_position = self._number_or_none(payload.get("position"))
        if incoming_duration is not None or not active_state or not same_media:
            self._attr_media_duration = incoming_duration
        if incoming_position is not None or not active_state or not same_media:
            self._attr_media_position = incoming_position
        volume = self._number_or_none(payload.get("volume"))
        self._attr_volume_level = None if volume is None else max(0.0, min(1.0, volume / 100.0))
        if incoming_position is not None:
            self._attr_media_position_updated_at = datetime.now(timezone.utc)
        elif self._attr_media_position is None:
            self._attr_media_position_updated_at = None
        self.async_write_ha_state()

    @property
    def media_image_remotely_accessible(self) -> bool:
        """Always let Home Assistant proxy artwork, including the packaged logo."""
        return False

    async def async_get_media_image(self):
        """Return the bundled logo without contacting the VBot WebUI."""
        if self._attr_media_image_url == _LOCAL_LOGO_URL:
            try:
                content = await self._hass.async_add_executor_job(_LOCAL_LOGO_PATH.read_bytes)
                return content, "image/png"
            except OSError as error:
                _LOGGER.warning("Không thể đọc ảnh media dự phòng tích hợp: %s", error)
                return None, None
        return await super().async_get_media_image()

    @staticmethod
    def _number_or_none(value):
        if isinstance(value, str) and ":" in value:
            try:
                parts = [int(part) for part in value.split(":")]
                if len(parts) == 3:
                    return float(parts[0] * 3600 + parts[1] * 60 + parts[2])
                if len(parts) == 2:
                    return float(parts[0] * 60 + parts[1])
            except (ValueError, OverflowError):
                return None
        try:
            number = float(value) if value is not None else None
            if number is not None and not math.isfinite(number):
                return None
            if number is not None and number > 10000:
                number /= 1000.0
            return number
        except (TypeError, ValueError, OverflowError):
            return None

    @property
    def state(self):
        return self._attr_state

    @property
    def media_title(self):
        return self._media_title

    async def async_play_media(self, media_type: str, media_id: str, **kwargs):
        from homeassistant.components import media_source

        source_metadata = {}
        if media_source.is_media_source_id(media_id):
            from .media_source import media_source_metadata

            source_metadata = media_source_metadata(media_id)
            if source_metadata.get("action") == "playlist":
                playlist_id = str(source_metadata.get("playlist_id") or "").strip()
                if not playlist_id:
                    raise ValueError("Playlist VBot không có ID hợp lệ")
                playlist_name = str(source_metadata.get("title") or "Playlist")
                await mqtt.async_publish(
                    self._hass,
                    f"{self._device}/script/playlist_control/set",
                    json.dumps({"action": "play", "playlist_id": playlist_id}),
                    qos=1,
                    retain=False,
                )
                self._media_title = playlist_name
                self._attr_media_playlist = playlist_name
                self._attr_state = MediaPlayerState.PLAYING
                self._attr_media_image_url = self._default_cover_url
                self.async_write_ha_state()
                return
            play_item = await media_source.async_resolve_media(
                self.hass,
                media_id,
                target_media_player=self.entity_id,
            )
            media_type = play_item.mime_type
            media_id = str(play_item.path) if play_item.path is not None else play_item.url
            if play_item.path is None and media_id.startswith("/") and not media_id.startswith("//"):
                from homeassistant.components.media_player.browse_media import async_process_play_media_url

                media_id = async_process_play_media_url(self.hass, media_id)
        self._media_url = media_id
        metadata = {**source_metadata, **(kwargs.get("metadata") or {})}
        supplied_title = kwargs.get("title") or metadata.get("title") or metadata.get("name")
        media_path = unquote(urlsplit(media_id).path)
        self._media_title = str(supplied_title or posixpath.basename(media_path) or media_id)
        self._attr_state = MediaPlayerState.PLAYING
        supplied_cover = kwargs.get("media_image_url", "") or metadata.get("thumbnail", "")
        self._attr_media_image_url = supplied_cover or self._default_cover_url

        #_LOGGER.info("Yêu cầu phát media:")
        #_LOGGER.info("  - Loại: %s", media_type)
        #_LOGGER.info("  - URL: %s", self._media_url)
        #_LOGGER.info("  - Tên file: %s", self._media_title)

        payload = {
            "action": "play",
            "media_link": self._media_url,
            "media_name": self._media_title,
            "media_player_source": metadata.get("source_label") or metadata.get("source") or "MQTT",
            "media_cover": supplied_cover
        }

        await mqtt.async_publish(
            self._hass,
            f"{self._device}/script/media_control/set",
            json.dumps(payload),
            qos=1,
            retain=False
        )
        self.async_write_ha_state()

    async def async_browse_media(
        self,
        media_content_type: str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Open this VBot's own branch in Home Assistant's media browser."""
        from homeassistant.components import media_source

        source_id = media_content_id or f"media-source://{DOMAIN}/{self._entry_id}"
        return await media_source.async_browse_media(self.hass, source_id)

    async def async_search_media(self, query: SearchMediaQuery) -> SearchMedia:
        """Search WebUI media providers for this VBot."""
        from homeassistant.components import media_source

        return await media_source.async_search_media(
            self.hass,
            f"media-source://{DOMAIN}/{self._entry_id}",
            query,
        )

    async def async_media_stop(self):
        #_LOGGER.info("Dừng phát media")
        self._attr_state = MediaPlayerState.IDLE
        await mqtt.async_publish(
            self._hass,
            f"{self._device}/script/media_control/set",
            "STOP",
            qos=1,
            retain=False
        )
        self.async_write_ha_state()

    async def async_media_pause(self):
        #_LOGGER.info("Tạm dừng media")
        self._attr_state = MediaPlayerState.PAUSED
        await mqtt.async_publish(
            self._hass,
            f"{self._device}/script/media_control/set",
            "PAUSE",
            qos=1,
            retain=False
        )
        self.async_write_ha_state()

    async def async_media_play(self):
        # Khi loa đang rảnh thì không có phiên media để resume. Cả loa chủ và
        # Phicomm R1 đều phát playlist mặc định khi người dùng nhấn Play.
        if self._attr_state == MediaPlayerState.IDLE:
            topic = f"{self._device}/script/playlist_control/set"
            payload = "PLAY"
        else:
            topic = f"{self._device}/script/media_control/set"
            payload = "RESUME"

        self._attr_state = MediaPlayerState.PLAYING
        await mqtt.async_publish(
            self._hass,
            topic,
            payload,
            qos=1,
            retain=False
        )
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        value = round(max(0.0, min(1.0, volume)) * 100)
        await mqtt.async_publish(
            self._hass,
            f"{self._device}/number/volume/set",
            str(value),
            qos=1,
            retain=False,
        )

    async def async_mute_volume(self, mute: bool) -> None:
        await mqtt.async_publish(
            self._hass,
            f"{self._device}/script/volume_control/set",
            "mute" if mute else "unmute",
            qos=1,
            retain=False,
        )

    async def async_media_seek(self, position: float) -> None:
        payload = json.dumps({"action": "seek", "set_duration": max(0, round(position))})
        await mqtt.async_publish(
            self._hass, f"{self._device}/script/media_control/set",
            payload, qos=1, retain=False
        )

    async def async_media_next_track(self) -> None:
        await mqtt.async_publish(
            self._hass, f"{self._device}/script/playlist_control/set",
            "next", qos=1, retain=False
        )

    async def async_media_previous_track(self) -> None:
        await mqtt.async_publish(
            self._hass, f"{self._device}/script/playlist_control/set",
            "prev", qos=1, retain=False
        )

    @property
    def extra_state_attributes(self):
        return {
            "source_kind": self._source_kind,
            "media_url": self._media_url,
            "playlist_active": getattr(self, "_playlist_active", False),
            "playlist_index": getattr(self, "_playlist_index", None),
            "playlist_total": getattr(self, "_playlist_total", 0),
            "playlist_loop": getattr(self, "_playlist_loop", False),
            "playlist_id": getattr(self, "_playlist_id", None),
            "playlist_name": getattr(self, "_playlist_name", None),
            "multiroom_connected": bool(
                self._multiroom.get("connected")
                or self._multiroom.get("coordinator")
            ),
            "multiroom_group_id": self._multiroom.get("group_id"),
            "multiroom_coordinator": self._multiroom.get("coordinator_name") or self._multiroom.get("coordinator_host"),
            "multiroom_has_media": bool(self._multiroom.get("has_media")),
            "multiroom_paused": bool(self._multiroom.get("paused")),
        }

    @property
    def device_info(self):
        if not self._device:
            return None
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT"
        }
