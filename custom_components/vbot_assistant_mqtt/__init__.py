from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.components import conversation

from .const import DOMAIN, CONF_DEVICE_ID
#from .conversation_agent import VBotAssistantConversationAgent
from .conversation_agent import VBotAssistantConversationAgent, VBotChatboxConversationAgent


async def async_setup(hass: HomeAssistant, config: dict):
    """Hàm khởi tạo chung, không làm gì nếu không dùng YAML."""
    return True


# Nếu vẫn giữ lại đoạn TTS engine cũ thì để nguyên, còn không thì xóa luôn cả hàm bên dưới:
# async def async_get_tts_engine(hass, config, discovery_info=None):
#     return await async_get_engine(hass, config, discovery_info)


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Gọi khi người dùng thêm 1 cấu hình integration."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    device_id = entry.data.get(CONF_DEVICE_ID)
    if device_id:
        agent = VBotAssistantConversationAgent(hass, entry, device_id)
        conversation.async_set_agent(hass, entry, agent)

        # Agent 2: Chatbox (dùng ID riêng)
        chatbox_agent = VBotChatboxConversationAgent(hass, entry, device_id)
        conversation.async_set_agent(hass, entry, chatbox_agent, agent_id=f"{device_id}_chatbox")

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
