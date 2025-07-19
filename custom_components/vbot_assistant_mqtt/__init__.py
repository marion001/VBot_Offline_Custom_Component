from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.components import conversation

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    VBot_PROCESSING_MODE,
)
from .conversation_agent import (
    VBotAssistantConversationAgent,
    VBotChatboxConversationAgent,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Hàm khởi tạo chung, không làm gì nếu không dùng YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Gọi khi người dùng thêm 1 cấu hình integration."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    device_id = entry.data.get(CONF_DEVICE_ID)
    processing_mode = entry.data.get(VBot_PROCESSING_MODE, "chatbot")  # Mặc định là 'chatbot'

    if device_id:
        # Khởi tạo agent theo chế độ được chọn
        if processing_mode == "chatbot":
            agent = VBotChatboxConversationAgent(hass, entry, device_id)
        else:
            agent = VBotAssistantConversationAgent(hass, entry, device_id)

        conversation.async_set_agent(hass, entry, agent)

    await hass.config_entries.async_forward_entry_setups(
        entry,
        ["switch", "number", "sensor", "select", "button", "text", "media_player"]
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Gỡ bỏ khi người dùng xóa cấu hình."""
    await hass.config_entries.async_unload_platforms(
        entry,
        ["switch", "number", "sensor", "select", "button", "text", "media_player"]
    )
    hass.data[DOMAIN].pop(entry.entry_id, None)
    conversation.async_unset_agent(hass, entry)
    return True
