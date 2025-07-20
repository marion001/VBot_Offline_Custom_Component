import voluptuous as vol
from homeassistant import config_entries
from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    VBot_URL_API
)


class VBotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.device_id = None

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input:
            self.device_id = user_input[CONF_DEVICE_ID].strip()
            url_api = user_input[VBot_URL_API].strip()

            # ✅ Kiểm tra trùng device_id với các entry đã tồn tại
            for entry in self._async_current_entries():
                if entry.data.get(CONF_DEVICE_ID) == self.device_id:
                    errors["base"] = "device_exists"
                    break

            if not errors:
                return self.async_create_entry(
                    title=f"VBot Assistant - (Tên Client MQTT: {self.device_id})",
                    data={
                        CONF_DEVICE_ID: self.device_id,
                        VBot_URL_API: url_api,
                    },
                    options={
                        VBot_URL_API: url_api,
                    }
                )

        schema = vol.Schema({
            vol.Required(CONF_DEVICE_ID, default="VBot"): str,
            vol.Required(VBot_URL_API, default="192.168.14.113:5002"): str,
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return VBotOptionsFlowHandler(config_entry)


# ✅ Giao diện "Cấu hình lại"
class VBotOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_url = self._config_entry.options.get(
            VBot_URL_API,
            self._config_entry.data.get(VBot_URL_API, "192.168.14.113:5002")
        )

        schema = vol.Schema({
            vol.Required(VBot_URL_API, default=current_url): str,
        })

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
