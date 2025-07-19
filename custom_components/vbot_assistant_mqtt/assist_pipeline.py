import logging
from homeassistant.core import HomeAssistant
from homeassistant.components import mqtt
from homeassistant.components.assist_pipeline.agent import AbstractAssistAgent

_LOGGER = logging.getLogger(__name__)

class VBotAssistAgent(AbstractAssistAgent):
    def __init__(self, hass: HomeAssistant, device_id: str):
        self.hass = hass
        self.device_id = device_id

    @property
    def name(self) -> str:
        # Hiển thị chính xác như yêu cầu
        return f"VBot Assist MQTT ({self.device_id})"

    @property
    def id(self) -> str:
        # ID định danh duy nhất
        return f"vbot_{self.device_id}"

    @property
    def supported_languages(self) -> list[str]:
        return ["vi"]

    async def async_process(self, text_input: str, context=None):
        """Gửi câu lệnh đến VBot qua MQTT"""
        topic = f"{self.device_id}/script/main_processing/set"
        try:
            await mqtt.async_publish(self.hass, topic, text_input, qos=1, retain=False)
            _LOGGER.debug(f"[AssistAgent] Đã gửi tới {topic}: {text_input}")
        except Exception as e:
            _LOGGER.error(f"[AssistAgent] Gửi MQTT lỗi: {e}")

        return {
            "plain_speech": {"speech": "VBot đã nhận lệnh."},
            "success": True
        }
