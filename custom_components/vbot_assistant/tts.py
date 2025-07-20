import logging
from homeassistant.components.tts import Provider
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

# Hàm gọi khi TTS platform khởi tạo từ config entry
async def async_get_engine(hass: HomeAssistant, config: dict, discovery_info=None):
    """Khởi tạo TTS engine cho VBot."""
    device = config.get("device") or config.get("entry_id") or "vbot"
    return VBotTTSProvider(hass, device)

# Lớp xử lý TTS riêng cho từng device
class VBotTTSProvider(Provider):
    def __init__(self, hass: HomeAssistant, device: str):
        self.hass = hass
        self.device = device
        self._name = f"VBot TTS ({device})"
        self._supported_languages = ["vi"]

    @property
    def default_language(self):
        return "vi"

    @property
    def supported_languages(self):
        return self._supported_languages

    @property
    def supported_options(self):
        return []

    @property
    def default_options(self):
        return {}

    @property
    def name(self):
        return self._name

    async def async_get_tts_audio(self, message: str, language: str, options=None):
        """Gửi nội dung TTS đến MQTT topic."""
        topic = f"{self.device}/script/vbot_tts/set"
        _LOGGER.info(f"[TTS] Gửi tới {topic}: {message}")
        await self.hass.components.mqtt.async_publish(topic, message, qos=1, retain=False)

        # Trả về dummy audio (Home Assistant yêu cầu có media type và bytes)
        return ("mp3", b"ID3")  # Dummy dữ liệu audio (nếu bạn không cần phát trong HA)
