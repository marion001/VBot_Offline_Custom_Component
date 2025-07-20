from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.components import conversation

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    VBot_URL_API,
)

from .conversation_agent import VBotConversationAgent

#Hàm khởi tạo chung, không làm gì nếu không dùng YAML
async def async_setup(hass: HomeAssistant, config: dict):
    return True

#Gọi khi người dùng thêm 1 cấu hình integration
async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    device_id = entry.data.get(CONF_DEVICE_ID)
    url_api = entry.options.get(VBot_URL_API, entry.data.get(VBot_URL_API, "192.168.14.113:5002"))
    if device_id:
        agent = VBotConversationAgent(hass, entry, device_id)
        conversation.async_set_agent(hass, entry, agent)

    await hass.config_entries.async_forward_entry_setups(
        entry,
        ["switch", "number", "sensor", "select", "button", "text", "media_player"]
    )
    return True

#Gỡ bỏ khi người dùng xóa cấu hình
async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    await hass.config_entries.async_unload_platforms(
        entry,
        ["switch", "number", "sensor", "select", "button", "text", "media_player"]
    )
    hass.data[DOMAIN].pop(entry.entry_id, None)
    conversation.async_unset_agent(hass, entry)
    return True
