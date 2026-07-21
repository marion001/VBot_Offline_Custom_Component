'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

import logging
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit
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
from .const import (
    DOMAIN, CONF_DEVICE_ID, VBot_URL_API,
    CONF_DEVICE_TYPE, DEVICE_TYPE_ANDROID, normalize_vbot_url,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    device = entry.data.get(CONF_DEVICE_ID)
    if not device:
        _LOGGER.error("Không tìm thấy device_id trong cấu hình")
        return

    api_url = entry.options.get(VBot_URL_API, entry.data.get(VBot_URL_API, ""))
    use_host_default_cover = entry.data.get(CONF_DEVICE_TYPE) != DEVICE_TYPE_ANDROID
    async_add_entities([
        VBotMediaPlayer(hass, device, api_url, use_host_default_cover)
    ])

class VBotMediaPlayer(MediaPlayerEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        device: str,
        api_url: str = "",
        use_host_default_cover: bool = False,
    ):
        self._hass = hass
        self._device = device
        self._attr_name = f"Media Player ({device})"
        self._attr_unique_id = f"{device.lower()}_media_player"
        self._attr_state = MediaPlayerState.IDLE
        self._attr_supported_features = (
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
        self._is_host_device = use_host_default_cover
        self._default_cover_url = (
            self._build_host_default_cover_url(api_url)
            if use_host_default_cover else None
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        unsubscribe = await mqtt.async_subscribe(
            self._hass,
            f"{self._device}/media_player/state",
            self._handle_state_message,
            qos=1,
        )
        self.async_on_remove(unsubscribe)
        unsubscribe_availability = await mqtt.async_subscribe(
            self._hass,
            f"{self._device}/availability",
            self._handle_availability_message,
            qos=1,
        )
        self.async_on_remove(unsubscribe_availability)

    @callback
    def _handle_availability_message(self, message) -> None:
        self._attr_available = str(message.payload).strip().lower() == "online"
        self.async_write_ha_state()

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
            self._attr_available = False
            self.async_write_ha_state()
            return

        state_mapping = {
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
            "idle": MediaPlayerState.IDLE,
        }
        self._attr_available = True
        self._attr_state = state_mapping.get(state, MediaPlayerState.IDLE)
        self._media_title = payload.get("title")
        self._attr_media_artist = payload.get("artist")
        self._attr_media_album_name = payload.get("album")
        self._media_url = payload.get("media_url")
        cover = str(payload.get("cover") or "").strip()
        self._attr_media_image_url = (
            cover
            or (self._default_cover_url if self._attr_state in (
                MediaPlayerState.PLAYING, MediaPlayerState.PAUSED
            ) else None)
        )
        self._attr_source = payload.get("source")
        self._source_kind = payload.get("source_kind")
        self._playlist_active = bool(payload.get("playlist_active"))
        self._playlist_index = payload.get("playlist_index")
        self._playlist_total = payload.get("playlist_total", 0)
        self._playlist_loop = bool(payload.get("playlist_loop"))
        self._attr_media_duration = self._number_or_none(payload.get("duration"))
        self._attr_media_position = self._number_or_none(payload.get("position"))
        volume = self._number_or_none(payload.get("volume"))
        self._attr_volume_level = None if volume is None else max(0.0, min(1.0, volume / 100.0))
        if self._attr_media_position is not None:
            self._attr_media_position_updated_at = datetime.now(timezone.utc)
        else:
            self._attr_media_position_updated_at = None
        self.async_write_ha_state()

    @staticmethod
    def _build_host_default_cover_url(api_url: str):
        normalized = normalize_vbot_url(api_url)
        if not normalized:
            return None
        parsed = urlsplit(normalized)
        if not parsed.hostname:
            return None
        host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        return f"{parsed.scheme or 'http'}://{host}/assets/img/logo.png"

    @staticmethod
    def _number_or_none(value):
        if isinstance(value, str) and ":" in value:
            try:
                parts = [int(part) for part in value.split(":")]
                if len(parts) == 3:
                    return float(parts[0] * 3600 + parts[1] * 60 + parts[2])
                if len(parts) == 2:
                    return float(parts[0] * 60 + parts[1])
            except ValueError:
                return None
        try:
            number = float(value) if value is not None else None
            if number is not None and number > 10000:
                number /= 1000.0
            return number
        except (TypeError, ValueError):
            return None

    @property
    def state(self):
        return self._attr_state

    @property
    def media_title(self):
        return self._media_title

    async def async_play_media(self, media_type: str, media_id: str, **kwargs):
        self._media_url = media_id
        self._media_title = media_id.split("/")[-1]
        self._attr_state = MediaPlayerState.PLAYING

        #_LOGGER.info("Yêu cầu phát media:")
        #_LOGGER.info("  - Loại: %s", media_type)
        #_LOGGER.info("  - URL: %s", self._media_url)
        #_LOGGER.info("  - Tên file: %s", self._media_title)

        payload = {
            "action": "play",
            "media_link": self._media_url,
            "media_name": self._media_title,
            "media_player_source": "MQTT",
            "media_cover": kwargs.get("media_image_url", "") or (kwargs.get("metadata") or {}).get("thumbnail", "")
        }

        await mqtt.async_publish(
            self._hass,
            f"{self._device}/script/media_control/set",
            json.dumps(payload),
            qos=1,
            retain=False
        )
        self.async_write_ha_state()

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
        # Nếu loa chủ đang rảnh thì không có phiên media để tiếp tục;
        # lúc này nút Play sẽ phát playlist mặc định.
        if self._is_host_device and self._attr_state == MediaPlayerState.IDLE:
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
