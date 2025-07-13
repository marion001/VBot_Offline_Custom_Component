from .const import DOMAIN

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    #Thêm các platform entry_id cần dùng
    await hass.config_entries.async_forward_entry_setups(
        #entry, ["switch", "number", "sensor", "select", "script", "input_text"]
        entry, ["switch", "number", "sensor", "select", "button", "input_text_entity"]
    )
    return True

async def async_unload_entry(hass, entry):
    #Gỡ tất cả các platform entry_id đã thêm vào trước đó
    await hass.config_entries.async_unload_platforms(
        #entry, ["switch", "number", "sensor", "select", "script", "input_text"]
        entry, ["switch", "number", "sensor", "select", "button", "input_text_entity"]
    )
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
