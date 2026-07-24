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
from .const import (
    DOMAIN, TTS_DOMAIN, CONF_DEVICE_ID, VBot_URL_API, CONF_API_KEY,
    CONF_DEVICE_TYPE, CONF_AUTO_UPDATE_URL, CONF_URL_SOURCE,
    URL_SOURCE_MANUAL, URL_SOURCE_MDNS,
    DEVICE_TYPE_HOST, DEVICE_TYPE_ANDROID, DEVICE_TYPE_ESP32,
    normalize_vbot_url, platforms_for_device,
)
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


async def async_migrate_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Migrate legacy entries without changing their identity or entities."""
    if entry.version > 3:
        return False
    if entry.version == 3:
        return True

    data = dict(entry.data)
    options = dict(entry.options)
    device_type = data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_HOST)
    if device_type not in (
        DEVICE_TYPE_HOST,
        DEVICE_TYPE_ANDROID,
        DEVICE_TYPE_ESP32,
    ):
        device_type = DEVICE_TYPE_HOST
    raw_url = options.get(VBot_URL_API, data.get(VBot_URL_API, ""))
    normalized_url = normalize_vbot_url(raw_url, device_type)

    # Legacy entries are intentionally treated as manual so an mDNS
    # advertisement cannot unexpectedly replace a user-configured address.
    source = options.get(
        CONF_URL_SOURCE,
        data.get(CONF_URL_SOURCE, URL_SOURCE_MANUAL),
    )
    if source not in (URL_SOURCE_MANUAL, URL_SOURCE_MDNS):
        source = URL_SOURCE_MANUAL
    auto_update = bool(
        options.get(
            CONF_AUTO_UPDATE_URL,
            data.get(CONF_AUTO_UPDATE_URL, source == URL_SOURCE_MDNS),
        )
    )
    source = URL_SOURCE_MDNS if auto_update else URL_SOURCE_MANUAL

    data.update({
        CONF_DEVICE_TYPE: device_type,
        VBot_URL_API: normalized_url,
        CONF_API_KEY: str(
            options.get(CONF_API_KEY, data.get(CONF_API_KEY, ""))
        ).strip(),
        CONF_AUTO_UPDATE_URL: auto_update,
        CONF_URL_SOURCE: source,
    })
    options.update({
        VBot_URL_API: normalized_url,
        CONF_API_KEY: str(
            options.get(CONF_API_KEY, data.get(CONF_API_KEY, ""))
        ).strip(),
        CONF_AUTO_UPDATE_URL: auto_update,
        CONF_URL_SOURCE: source,
    })
    hass.config_entries.async_update_entry(
        entry,
        data=data,
        options=options,
        version=3,
    )
    return True

#Gọi khi người dùng thêm 1 cấu hình integration
async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    device_id = entry.data.get(CONF_DEVICE_ID)
    if device_id and entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_HOST:
        agent = VBotConversationAgent(hass, entry, device_id)
        conversation.async_set_agent(hass, entry, agent)
    await hass.config_entries.async_forward_entry_setups(
        entry, platforms_for_device(entry.data)
    )
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Nạp lại agent khi URL API trong Options thay đổi."""
    await hass.config_entries.async_reload(entry.entry_id)

#Gỡ bỏ khi người dùng xóa cấu hình
async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    await hass.config_entries.async_unload_platforms(
        entry, platforms_for_device(entry.data)
    )
    hass.data[DOMAIN].pop(entry.entry_id, None)
    if entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_HOST:
        conversation.async_unset_agent(hass, entry)
    return True
