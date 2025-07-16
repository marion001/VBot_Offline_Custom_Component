import logging
from homeassistant.components.tts import Provider
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import DiscoveryInfoType
from .const import CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)


async def async_get_engine(
    hass: HomeAssistant,
    config: dict,
    discovery_info: DiscoveryInfoType | None = None
) -> Provider | None:
    """Trả về engine TTS từ config entry (không cần YAML)."""
    if discovery_info is None:
        _LOGGER.error("[TTS] Không có discovery_info")
        return None

    device_id = discovery_info.get(CONF_DEVICE_ID)
    if not device_id:
        _LOGGER.error("[TTS] Không tìm thấy device_id trong discovery_info")
        return None

    return VBotTTSProvider(hass, device_id)


class VBotTTSProvider(Provider):
    """TTS provider cho thiết bị VBot gửi MQTT."""

    def __init__(self, hass: HomeAssistant, device_id: str):
        self.hass = hass
        self._device_id = device_id
        self._provider_name = f"{device_id}_tts_speak"

    @property
    def name(self) -> str:
        """Tên dùng trong entity_id: tts.<name>"""
        return self._provider_name.lower()

    @property
    def default_language(self) -> str:
        return "vi"

    @property
    def supported_languages(self) -> list[str]:
        return ["vi"]

    @property
    def supported_options(self) -> list[str]:
        return []

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict | None = None
    ) -> tuple[str, bytes] | None:
        topic = f"{self._device_id}/script/vbot_tts/set"
        try:
            await mqtt.async_publish(
                self.hass,
                topic,
                message,
                qos=1,
                retain=False
            )
            _LOGGER.debug(f"[TTS] Đã gửi MQTT đến {topic}: {message}")
        except Exception as e:
            _LOGGER.error(f"[TTS] Lỗi khi gửi MQTT: {e}")
        return ("mp3", b"")  # Trả về dữ liệu giả để HA không báo lỗi
