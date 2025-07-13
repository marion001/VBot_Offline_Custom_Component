from .const import DOMAIN

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    #Thêm tất cả các platform cần dùng
    await hass.config_entries.async_forward_entry_setups(
        entry, ["switch", "number", "sensor", "select"]
    )
    return True

async def async_unload_entry(hass, entry):
    #Gỡ tất cả các platform đã forward
    await hass.config_entries.async_unload_platforms(
        entry, ["switch", "number", "sensor", "select"]
    )
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
