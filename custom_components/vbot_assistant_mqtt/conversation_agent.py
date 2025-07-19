import logging
from homeassistant.components import mqtt
from homeassistant.components import conversation
from homeassistant.helpers import intent

_LOGGER = logging.getLogger(__name__)

class VBotAssistantConversationAgent(conversation.AbstractConversationAgent):
    def __init__(self, hass, entry, device_id: str):
        self.hass = hass
        self.entry = entry
        self.device_id = device_id

    @property
    def supported_languages(self) -> list[str]:
        return ["vi"]

    @property
    def name(self) -> str:
        # 👇 Tên hiển thị trong giao diện Assist
        return f"VBot Assist MQTT ({self.device_id})"

    async def async_process(self, user_input: conversation.ConversationInput) -> conversation.ConversationResult:
        message = user_input.text or "Không có đầu vào"
        topic = f"{self.device_id}/script/main_processing/set"

        try:
            await mqtt.async_publish(self.hass, topic, message, qos=1, retain=False)
            _LOGGER.info(f"[VBot] Gửi tới {topic}: {message}")
            response_text = "Đã gửi lệnh tới VBot."
        except Exception as e:
            _LOGGER.error(f"[VBot] Lỗi khi gửi MQTT: {e}")
            response_text = "Không thể gửi lệnh tới thiết bị."

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id
        )
