import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_DEVICE_ID

class VBotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    def __init__(self):
        self.device_id = None

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            self.device_id = user_input[CONF_DEVICE_ID].strip()
            return self.async_create_entry(title=self.device_id, data={CONF_DEVICE_ID: self.device_id})

        schema = vol.Schema({vol.Required(CONF_DEVICE_ID, default="VBot"): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
