import logging
from homeassistant.components import mqtt
from homeassistant.components import conversation
from homeassistant.helpers import intent

_LOGGER = logging.getLogger(__name__)

class VBotConversationAgent(conversation.AbstractConversationAgent):
    def __init__(self, hass, entry, device_id: str):
        self.hass = hass
        self.entry = entry
        self.device_id = device_id

    @property
    def supported_languages(self) -> list[str]:
        return ["vi"]

    async def async_process(self, user_input: conversation.ConversationInput) -> conversation.ConversationResult:
        message = user_input.text or "Không có đầu vào"

        # 👉 Lấy trạng thái của entity select chọn luồng xử lý
        #select.che_do_xu_ly_tac_nhan_assist_vbot_dev_222
        select_entity_id = f"select.assist_tac_nhan_che_do_xu_ly_{self.device_id.lower()}"
        select_state = self.hass.states.get(select_entity_id)
        processing_mode = select_state.state if select_state else "chatbot"

        # 👉 Xác định topic theo chế độ xử lý
        if processing_mode == "main_processing":
            topic = f"{self.device_id}/script/main_processing/set"
        else:
            topic = f"{self.device_id}/script/chatbot_processing/set"

        try:
            await mqtt.async_publish(self.hass, topic, message, qos=1, retain=False)
            _LOGGER.info(f"[VBot] Gửi tới {topic}: {message}")
            response_text = f"Đã gửi tới chế độ: {processing_mode}."
        except Exception as e:
            _LOGGER.error(f"[VBot] Lỗi khi gửi MQTT: {e}")
            response_text = "Không thể gửi lệnh tới thiết bị."

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id
        )
