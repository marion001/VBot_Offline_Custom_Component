'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.components import conversation
from homeassistant.components import mqtt
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from .const import (DOMAIN, TTS_DOMAIN, CONF_DEVICE_ID, VBot_URL_API)
from .conversation_agent import VBotConversationAgent

#Hàm khởi tạo chung, không làm gì nếu không dùng YAML
async def async_setup(hass: HomeAssistant, config: dict):
    async def handle_tts(call):
        message = str(call.data.get("message", call.data.get("text", ""))).strip()
        device_id = str(call.data.get(CONF_DEVICE_ID, "")).strip()
        if not message or not device_id:
            return
        await mqtt.async_publish(
            hass,
            f"{device_id}/script/vbot_tts/set",
            message,
            qos=1,
            retain=False,
        )

    if not hass.services.has_service(TTS_DOMAIN, "say"):
        hass.services.async_register(
            TTS_DOMAIN,
            "say",
            handle_tts,
            schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): cv.string,
                vol.Exclusive("message", "content"): cv.string,
                vol.Exclusive("text", "content"): cv.string,
            }),
        )
    return True

#Gọi khi người dùng thêm 1 cấu hình integration
async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    device_id = entry.data.get(CONF_DEVICE_ID)
    if device_id:
        agent = VBotConversationAgent(hass, entry, device_id)
        conversation.async_set_agent(hass, entry, agent)
    await hass.config_entries.async_forward_entry_setups(
        entry,
        ["switch", "number", "sensor", "select", "button", "text", "media_player"]
    )
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Nạp lại agent khi URL API trong Options thay đổi."""
    await hass.config_entries.async_reload(entry.entry_id)

#Gỡ bỏ khi người dùng xóa cấu hình
async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    await hass.config_entries.async_unload_platforms(
        entry,
        ["switch", "number", "sensor", "select", "button", "text", "media_player"]
    )
    hass.data[DOMAIN].pop(entry.entry_id, None)
    conversation.async_unset_agent(hass, entry)
    return True
