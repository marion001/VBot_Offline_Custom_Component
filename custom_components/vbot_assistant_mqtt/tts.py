import logging
from homeassistant.components.tts import Provider
from homeassistant.components import mqtt
from .const import CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

async def async_get_engine(hass, config, discovery_info=None):
    # Lấy config entry từ config
    entry = config.get("entry")
    if entry is None:
        _LOGGER.error("[VBotTTS] Không tìm thấy config entry")
        return None

    device_id = entry.data.get(CONF_DEVICE_ID)
    if not device_id:
        _LOGGER.error("[VBotTTS] device_id trống")
        return None

    return VBotTTSProvider(hass, device_id)

class VBotTTSProvider(Provider):
    def __init__(self, hass, device_id):
        super().__init__()
        self.hass = hass
        self._device_id = device_id
        self._provider_name = f"{device_id}_tts_speak"

    @property
    def name(self):
        return self._provider_name.lower()

    @property
    def default_language(self):
        return "vi"

    @property
    def supported_languages(self):
        return ["vi"]

    @property
    def supported_options(self):
        return []

    async def async_get_tts_audio(self, message, language, options=None):
        topic = f"{self._device_id}/script/vbot_tts/set"
        try:
            await mqtt.async_publish(self.hass, topic, message, qos=1, retain=False)
            _LOGGER.debug(f"[VBotTTS] Gửi MQTT {topic}: {message}")
        except Exception as e:
            _LOGGER.error(f"[VBotTTS] Gửi MQTT lỗi: {e}")
        return "mp3", b""
