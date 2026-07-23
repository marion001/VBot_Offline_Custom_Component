'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

import logging
import asyncio
import aiohttp
from homeassistant.components import conversation
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import VBot_URL_API, normalize_vbot_url

_LOGGER = logging.getLogger(__name__)

class VBotConversationAgent(conversation.AbstractConversationAgent):
    def __init__(self, hass, entry, device_id: str):
        self.hass = hass
        self.entry = entry
        self.device_id = device_id
        self.base_url = normalize_vbot_url(
            entry.options.get(VBot_URL_API, entry.data.get(VBot_URL_API)),
            entry.data.get("device_type"),
        )

    @property
    def supported_languages(self) -> list[str]:
        return ["vi"]

    async def async_process(self, user_input: conversation.ConversationInput) -> conversation.ConversationResult:
        message = user_input.text
        if not message or not message.strip():
            #Trả lại kết quả cho Assist
            response_text = "Vui lòng nhập tin nhắn"
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(response_text)
            intent_response.async_set_card(
                title="VBot Assist",
                content=response_text
            )
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=user_input.conversation_id
            )
        mode_entity_id = f"select.assist_tac_nhan_che_do_xu_ly_{self.device_id.lower()}"
        stream_entity_id = f"select.assist_tac_nhan_luong_xu_ly_{self.device_id.lower()}"
        mode_state = self.hass.states.get(mode_entity_id)
        processing_mode = mode_state.state if mode_state else "chatbot"
        stream_state = self.hass.states.get(stream_entity_id)
        processing_stream = stream_state.state if stream_state else "api"
        vbot_mode = "chatbot" if "chatbot" in processing_mode else "processing"
        intent_response = intent.IntentResponse(language=user_input.language)
        try:
            #Nếu chọn Luồng API
            if processing_stream == "api":
                if not self.base_url:
                    raise ValueError("Chưa cấu hình URL API VBot")
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
                timeout = aiohttp.ClientTimeout(total=15)
                session = async_get_clientsession(self.hass)
                async with session.post(url, json=payload, headers=headers, timeout=timeout) as resp:
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
                            response_text = "Lỗi khi lấy dữ liệu phản hồi"
            else:
                raise ValueError(f"Luồng xử lý không hợp lệ: {processing_stream}")

        except asyncio.TimeoutError:
            response_text = "VBot chưa phản hồi, vui lòng thử lại."
        except (aiohttp.ClientError, ValueError) as e:
            _LOGGER.error(f"[VBot Assist] Lỗi khi gửi lệnh: {e}")
            response_text = "Không thể gửi lệnh tới thiết bị."
        except Exception as e:
            _LOGGER.exception("[VBot Assist] Lỗi xử lý phản hồi ngoài dự kiến: %s", e)
            response_text = "VBot trả về dữ liệu không hợp lệ."

        #Trả lại kết quả cho Assist
        intent_response.async_set_speech(response_text)
        intent_response.async_set_card(
            title="VBot Assist",
            content=response_text
        )
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id
        )
