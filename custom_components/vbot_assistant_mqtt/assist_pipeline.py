import logging
from homeassistant.core import HomeAssistant
from homeassistant.components import mqtt

_LOGGER = logging.getLogger(__name__)

class VBotAssistAgent:
    """Agent tùy chỉnh đơn giản mà không kế thừa AbstractAssistAgent"""

    def __init__(self, hass: HomeAssistant, device_id: str):
        self.hass = hass
        self.device_id = device_id

    @property
    def name(self) -> str:
        return f"VBot Assist MQTT ({self.device_id})"

    @property
    def id(self) -> str:
        return f"vbot_{self.device_id}"

    @property
    def supported_languages(self) -> list[str]:
        return ["vi"]

    async def async_process(self, text_input: str, context=None):
        topic = f"{self.device_id}/script/main_processing/set"
        try:
            await mqtt.async_publish(self.hass, topic, text_input, qos=1, retain=False)
            _LOGGER.debug(f"[VBotAssistAgent] Gửi '{text_input}' đến {topic}")
        except Exception as e:
            _LOGGER.error(f"[VBotAssistAgent] Lỗi gửi MQTT: {e}")

        return {
            "plain_speech": {"speech": "VBot đã nhận lệnh."},
            "success": True,
        }
