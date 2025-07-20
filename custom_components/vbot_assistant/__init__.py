from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.components import conversation
from homeassistant.components.tts import DOMAIN as TTS_DOMAIN
from .tts import VBotTTSProvider

from homeassistant.components import tts

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    VBot_URL_API,
)

from .conversation_agent import VBotConversationAgent

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

    # Đăng ký TTS Provider đúng cách
    provider = VBotTTSProvider(hass, {"device": device_id})
    tts.async_register_provider(hass, provider)

    # Forward các platform
    await hass.config_entries.async_forward_entry_setups(
        entry,
        ["switch", "number", "sensor", "select", "button", "text", "media_player", "tts"]
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    await hass.config_entries.async_unload_platforms(
        entry,
        ["switch", "number", "sensor", "select", "button", "text", "media_player", "tts"]
    )
    hass.data[DOMAIN].pop(entry.entry_id, None)
    conversation.async_unset_agent(hass, entry)
    return True
