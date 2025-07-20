from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.components import conversation
from homeassistant.components.tts import async_get_tts_manager

from .const import DOMAIN, CONF_DEVICE_ID, VBot_URL_API
from .conversation_agent import VBotConversationAgent
from .tts import VBotTTSProvider

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    device_id = entry.data.get(CONF_DEVICE_ID)
    url_api = entry.options.get(VBot_URL_API, entry.data.get(VBot_URL_API, "192.168.14.113:5002"))

    # Đăng ký Conversation Agent
    if device_id:
        agent = VBotConversationAgent(hass, entry, device_id)
        conversation.async_set_agent(hass, entry, agent)

    # Đăng ký TTS Provider nếu Home Assistant mới
    provider = VBotTTSProvider(hass, {"device": device_id})
    manager = await async_get_tts_manager(hass)
    await manager.async_register_provider(provider)

    # Forward các platform
    await hass.config_entries.async_forward_entry_setups(
        entry,
        ["switch", "number", "sensor", "select", "button", "text", "media_player"]
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    await hass.config_entries.async_unload_platforms(
        entry,
        ["switch", "number", "sensor", "select", "button", "text", "media_player"]
    )
    hass.data[DOMAIN].pop(entry.entry_id, None)
    conversation.async_unset_agent(hass, entry)
    return True
