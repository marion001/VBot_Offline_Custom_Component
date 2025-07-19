from .const import DOMAIN
#from .tts import async_get_engine


async def async_setup(hass, config):
    return True

async def async_get_tts_engine(hass, config, discovery_info=None):
    return await async_get_engine(hass, config, discovery_info)

#Thêm các platform entry_id cần dùng
async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(
        entry, ["switch", "number", "sensor", "select", "button", "text", "media_player"]
    )
    return True

#Gỡ tất cả các platform entry_id đã thêm vào trước đó
async def async_unload_entry(hass, entry):
    await hass.config_entries.async_unload_platforms(
        entry, ["switch", "number", "sensor", "select", "button", "text", "media_player"]
    )
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

