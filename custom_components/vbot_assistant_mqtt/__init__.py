from .const import DOMAIN

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Đây là hàm đúng
    await hass.config_entries.async_forward_entry_setups(entry, ["switch", "number"])
    return True

async def async_unload_entry(hass, entry):
    await hass.config_entries.async_unload_platforms(entry, ["switch", "number"])
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

async def async_setup(hass, config):
    return True
