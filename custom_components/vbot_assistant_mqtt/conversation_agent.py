import logging
import aiohttp
from homeassistant.components import mqtt
from homeassistant.components import conversation
from homeassistant.helpers import intent

_LOGGER = logging.getLogger(__name__)

class VBotConversationAgent(conversation.AbstractConversationAgent):
    def __init__(self, hass, entry, device_id: str):
        self.hass = hass
        self.entry = entry
        self.device_id = device_id
        self.base_url = entry.data.get("vbot_url_api")  # ✅ Lấy URL API từ config

    @property
    def supported_languages(self) -> list[str]:
        return ["vi"]

    async def async_process(self, user_input: conversation.ConversationInput) -> conversation.ConversationResult:
        message = user_input.text or "Không có đầu vào"

        # 🧠 Lấy chế độ xử lý: chatbot / processing
        mode_entity_id = f"select.assist_tac_nhan_che_do_xu_ly_{self.device_id.lower()}"
        
        # 🧠 Lấy luồng xử lý: api / mqtt select.assist_tac_nhan_luong_xu_ly_vbot_dev_222_2
        stream_entity_id = f"select.assist_tac_nhan_luong_xu_ly_{self.device_id.lower()}"

        mode_state = self.hass.states.get(mode_entity_id)
        processing_mode = mode_state.state if mode_state else "chatbot"

        stream_state = self.hass.states.get(stream_entity_id)
        processing_stream = stream_state.state if stream_state else "mqtt"
        _LOGGER.info(f"[VBot] processing_stream: {processing_stream}")
        
        # 🔍 Chuẩn hóa lại chế độ xử lý: "chatbot" / "processing"
        vbot_mode = "chatbot" if "chatbot" in processing_mode else "processing"
        _LOGGER.info(f"[VBot] vbot_mode: {vbot_mode}")
        intent_response = intent.IntentResponse(language=user_input.language)

        try:
            if processing_stream == "mqtt":
                # 📡 Gửi qua MQTT
                topic = f"{self.device_id}/script/{processing_mode}/set"
                await mqtt.async_publish(self.hass, topic, message, qos=1, retain=False)
                _LOGGER.info(f"[VBot] Gửi MQTT tới {topic}: {message}")
                response_text = f"Đã gửi lệnh qua MQTT - chế độ: {processing_mode}."

            elif processing_stream == "api":
                # 🌐 Gửi qua API
                url = f"{self.base_url}/"
                payload = {
                    "type": 3,
                    "data": "main_processing",
                    "action": vbot_mode,
                    "value": message
                }
                headers = {
                    "Content-Type": "application/json"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("success") and "message" in data:
                                response_text = data["message"]
                            else:
                                _LOGGER.error(f"[VBot Assist] Lỗi định dạng phản hồi API: {data}")
                                response_text = f"Không có dữ liệu phản hồi: {data.get('message')}"
                        else:
                            error_body = await resp.text()
                            _LOGGER.error(f"[VBot Assist] Không thể lấy phản hồi từ API: {error_body}")
                            response_text = "Lỗi khi lấy phản hồi"

                _LOGGER.info(f"[VBot] Gửi API tới {url} với payload: {payload}")


            else:
                raise ValueError(f"Luồng xử lý không hợp lệ: {processing_stream}")

        except Exception as e:
            _LOGGER.error(f"[VBot] Lỗi khi gửi lệnh: {e}")
            response_text = "Không thể gửi lệnh tới thiết bị."

        # 🔁 Trả lại kết quả cho Assist
        intent_response.async_set_speech(response_text)
        intent_response.async_set_card(
            title="VBot Assistant",
            content=response_text
        )


        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id
        )
