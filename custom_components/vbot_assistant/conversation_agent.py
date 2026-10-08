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
        return ["vi", "en"]

    async def async_process(self, user_input: conversation.ConversationInput) -> conversation.ConversationResult:
        english = str(user_input.language or "").lower().startswith("en")
        def message_text(vi, en):
            return en if english else vi
        message = user_input.text
        from uuid import uuid4
        conversation_id = user_input.conversation_id or uuid4().hex
        if not message or not message.strip():
            #Trả lại kết quả cho Assist
            response_text = message_text("Vui lòng nhập tin nhắn", "Please enter a message")
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(response_text)
            intent_response.async_set_card(
                title="VBot Assist",
                content=response_text
            )
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=conversation_id
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
        if processing_mode not in {"chatbot", "processing"}:
            processing_mode = "chatbot"
        stream_state = self.hass.states.get(stream_entity_id) if stream_entity_id else None
        processing_stream = stream_state.state if stream_state else "api"
        if processing_stream in {"unknown", "unavailable"}:
            processing_stream = "api"
        vbot_mode = processing_mode
        intent_response = intent.IntentResponse(language=user_input.language)
        failed = False
        needs_clarification = False
        try:
            #Nếu chọn Luồng API
            if processing_stream == "api":
                if not self.runtime.api_url:
                    raise ValueError("Chưa cấu hình URL API VBot")
                payload = {
                    "type": 3,
                    "data": "main_processing",
                    "action": vbot_mode,
                    "value": message,
                    "response_type": "text",
                    "session_id": f'assist:{self.device_id}:{conversation_id}',
                }
                status, data = await self.runtime.client.async_post("", payload, timeout=self.entry.options.get("assist_timeout", 120))
                if status == 200:
                    if isinstance(data, dict) and data.get("success") is True and isinstance(data.get("message"), str) and data["message"].strip():
                        response_text = data["message"]
                        needs_clarification = vbot_mode == "processing" and data.get("needs_clarification") is True
                    else:
                        failed = True
                        _LOGGER.error("[VBot Assist] API không có phản hồi hợp lệ")
                        response_text = message_text("VBot không có dữ liệu phản hồi hợp lệ.", "VBot did not return a valid response.")
                else:
                    failed = True
                    _LOGGER.error("[VBot Assist] HTTP %s", status)
                    if status == 401:
                        self.entry.async_start_reauth_if_available(self.hass)
                    response_text = message_text("Lỗi khi lấy dữ liệu phản hồi", "Could not retrieve a response")
            else:
                raise ValueError(f"Luồng xử lý không hợp lệ: {processing_stream}")

        except asyncio.TimeoutError:
            failed = True
            response_text = message_text("VBot chưa phản hồi. Nếu đây là lệnh điều khiển, hãy kiểm tra trạng thái thiết bị trước khi gửi lại.", "VBot did not respond in time. For a control request, check the device state before sending it again.")
        except (aiohttp.ClientError, ValueError) as e:
            failed = True
            _LOGGER.error(f"[VBot Assist] Lỗi khi gửi lệnh: {e}")
            response_text = message_text("Không thể gửi lệnh tới thiết bị.", "Could not send the request to the device.")
        except Exception as e:
            failed = True
            _LOGGER.exception("[VBot Assist] Lỗi xử lý phản hồi ngoài dự kiến: %s", e)
            response_text = message_text("VBot trả về dữ liệu không hợp lệ.", "VBot returned invalid data.")

        #Trả lại kết quả cho Assist
        if failed:
            intent_response.async_set_error(intent.IntentResponseErrorCode.FAILED_TO_HANDLE, response_text)
        intent_response.async_set_speech(response_text)
        intent_response.async_set_card(
            title="VBot Assist",
            content=response_text
        )
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=conversation_id,
            continue_conversation=needs_clarification and not failed,
        )
