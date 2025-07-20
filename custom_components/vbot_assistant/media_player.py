import logging
import json
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, CONF_DEVICE_ID

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

    async_add_entities([VBotMediaPlayer(hass, device)])

class VBotMediaPlayer(MediaPlayerEntity):
    def __init__(self, hass: HomeAssistant, device: str):
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
        )
        self._media_title = None
        self._media_url = None

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
            "media_player_source": "MQTT"
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
        #_LOGGER.info("Tiếp tục phát media")
        self._attr_state = MediaPlayerState.PLAYING
        await mqtt.async_publish(
            self._hass,
            f"{self._device}/script/media_control/set",
            "RESUME",
            qos=1,
            retain=False
        )
        self.async_write_ha_state()

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
