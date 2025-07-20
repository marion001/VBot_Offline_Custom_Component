# custom_components/vbot_assistant/tts.py

from homeassistant.components.tts import Provider

class VBotTTSProvider(Provider):
    def __init__(self, hass, config):
        self.hass = hass
        self.device = config.get("device", "vbot")
        self._name = f"VBot TTS {self.device}"

    @property
    def default_language(self):
        return "vi"

    @property
    def supported_languages(self):
        return ["vi"]

    @property
    def supported_options(self):
        return []

    @property
    def default_options(self):
        return {}

    async def async_get_tts_audio(self, message, language, options=None):
        # Gửi message tới MQTT hoặc API ở đây
        return ("wav", b"")  # bạn thay đoạn này bằng audio thật

async def async_get_engine(hass, config, discovery_info=None):
    return VBotTTSProvider(hass, config)
