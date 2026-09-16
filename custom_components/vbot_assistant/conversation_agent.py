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
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN
from .runtime import VBotRuntimeData

_LOGGER = logging.getLogger(__name__)

class VBotConversationAgent(conversation.AbstractConversationAgent):
    def __init__(self, hass, entry, runtime: VBotRuntimeData):
        self.hass = hass
        self.entry = entry
        self.runtime = runtime
        self.device_id = runtime.device_id

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
        registry = er.async_get(self.hass)
        mode_entity_id = registry.async_get_entity_id(
            "select", DOMAIN,
            f"{self.device_id.lower()}_assist_processing_mode_select",
        )
        stream_entity_id = registry.async_get_entity_id(
            "select", DOMAIN,
            f"{self.device_id.lower()}_assist_stream_select",
        )
        mode_state = self.hass.states.get(mode_entity_id) if mode_entity_id else None
        processing_mode = mode_state.state if mode_state else "chatbot"
        stream_state = self.hass.states.get(stream_entity_id) if stream_entity_id else None
        processing_stream = stream_state.state if stream_state else "api"
        vbot_mode = "chatbot" if "chatbot" in processing_mode else "processing"
        intent_response = intent.IntentResponse(language=user_input.language)
        try:
            #Nếu chọn Luồng API
            if processing_stream == "api":
                if not self.runtime.api_url:
                    raise ValueError("Chưa cấu hình URL API VBot")
                payload = {
                    "type": 3,
                    "data": "main_processing",
                    "action": vbot_mode,
                    "value": message
                }
                status, data = await self.runtime.client.async_post("", payload)
                if status == 200:
                    if data.get("success") and "message" in data:
                        response_text = data["message"]
                    else:
                        _LOGGER.error(f"[VBot Assist] Lỗi định dạng phản hồi API: {data}")
                        response_text = f"Không có dữ liệu phản hồi: {data.get('message')}"
                else:
                    _LOGGER.error(f"[VBot Assist] Không thể lấy phản hồi từ API: {data}")
                    if status == 401:
                        self.entry.async_start_reauth_if_available(self.hass)
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
