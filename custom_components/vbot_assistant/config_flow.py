'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

import voluptuous as vol
from datetime import datetime, timezone
from urllib.parse import urlsplit
from homeassistant import config_entries
from homeassistant.components import persistent_notification
from .const import (
    DOMAIN, CONF_DEVICE_ID, VBot_URL_API, CONF_DEVICE_TYPE,
    DEVICE_TYPE_HOST, DEVICE_TYPE_ANDROID, DEVICE_TYPE_ESP32,
    CONF_AUTO_UPDATE_URL, CONF_URL_SOURCE, CONF_MDNS_LAST_UPDATE,
    URL_SOURCE_MANUAL, URL_SOURCE_MDNS,
    normalize_vbot_url,
)
#import logging
#_LOGGER = logging.getLogger(__name__)

class VBotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self.device_id = None

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            self.device_id = user_input[CONF_DEVICE_ID].strip()
            device_type = user_input.get(CONF_DEVICE_TYPE, DEVICE_TYPE_HOST)
            if device_type not in (DEVICE_TYPE_HOST, DEVICE_TYPE_ANDROID, DEVICE_TYPE_ESP32):
                device_type = DEVICE_TYPE_HOST
            url_api = normalize_vbot_url(user_input[VBot_URL_API], device_type)
            device_name = {
                DEVICE_TYPE_ANDROID: "Phicomm R1 Client",
                DEVICE_TYPE_ESP32: "ESP32 VBot Client",
            }.get(device_type, "VBot Assistant")
            await self.async_set_unique_id(self.device_id)
            self._abort_if_unique_id_configured()
            #Kiểm tra trùng thủ công
            for entry in self._async_current_entries():
                if entry.data.get(CONF_DEVICE_ID) == self.device_id:
                    errors["base"] = "device_exists"
                    break
            if not errors:
                persistent_notification.async_dismiss(self.hass, notification_id=f"vbot_discovered_{self.device_id}",)
                return self.async_create_entry(
                    title=f"{device_name} {urlsplit(url_api).hostname or url_api} - (Tên Client MQTT: {self.device_id})",
                    data={
                        CONF_DEVICE_ID: self.device_id,
                        VBot_URL_API: url_api,
                        CONF_DEVICE_TYPE: device_type,
                        CONF_AUTO_UPDATE_URL: False,
                        CONF_URL_SOURCE: URL_SOURCE_MANUAL,
                    },
                    options={
                        VBot_URL_API: url_api,
                        CONF_AUTO_UPDATE_URL: False,
                        CONF_URL_SOURCE: URL_SOURCE_MANUAL,
                    },
                )
        schema = vol.Schema({
            vol.Required(CONF_DEVICE_ID, default="VBot"): str,
            vol.Required(VBot_URL_API, default="192.168.14.113:5002"): str,
            vol.Required(CONF_DEVICE_TYPE, default=DEVICE_TYPE_HOST): vol.In({
                DEVICE_TYPE_HOST: "Loa Chủ VBot",
                DEVICE_TYPE_ANDROID: "Phicomm R1 Client",
                DEVICE_TYPE_ESP32: "ESP32 / ESP32-S3 Client",
            }),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    #Scan VBot mDNS
    async def async_step_zeroconf(self, discovery_info):
        properties = discovery_info.properties or {}
        device_id = properties.get("device_id", "").strip()
        device_name = (properties.get("name") or "VBot Assistant").strip()
        device_version = (properties.get("version") or "N/A").strip()
        device_type = (properties.get(CONF_DEVICE_TYPE) or DEVICE_TYPE_HOST).strip()
        if device_type not in (DEVICE_TYPE_HOST, DEVICE_TYPE_ANDROID, DEVICE_TYPE_ESP32):
            device_type = DEVICE_TYPE_HOST
        url_api = normalize_vbot_url(properties.get("url_api", ""), device_type)
        discovered_at = datetime.now(timezone.utc).isoformat()
        if not device_id or not url_api:
            return self.async_abort(reason="invalid_discovery_data")
        self._discovered_device = {
            CONF_DEVICE_ID: device_id,
            VBot_URL_API: url_api,
            CONF_DEVICE_TYPE: device_type,
            CONF_AUTO_UPDATE_URL: True,
            CONF_URL_SOURCE: URL_SOURCE_MDNS,
            CONF_MDNS_LAST_UPDATE: discovered_at,
            "name": device_name,
            "version": device_version,
        }
        await self.async_set_unique_id(device_id)
        existing_entry = next(
            (
                entry for entry in self._async_current_entries()
                if entry.unique_id == device_id
                or entry.data.get(CONF_DEVICE_ID) == device_id
            ),
            None,
        )
        if existing_entry is not None:
            auto_update = existing_entry.options.get(
                CONF_AUTO_UPDATE_URL,
                existing_entry.data.get(
                    CONF_AUTO_UPDATE_URL,
                    existing_entry.data.get(CONF_URL_SOURCE) == URL_SOURCE_MDNS,
                ),
            )
            if auto_update:
                current_url = normalize_vbot_url(
                    existing_entry.options.get(
                        VBot_URL_API,
                        existing_entry.data.get(VBot_URL_API, ""),
                    ),
                    existing_entry.data.get(CONF_DEVICE_TYPE, device_type),
                )
                if current_url != url_api:
                    updated_data = {**existing_entry.data, **self._discovered_device}
                    updated_options = {
                        **existing_entry.options,
                        VBot_URL_API: url_api,
                        CONF_AUTO_UPDATE_URL: True,
                        CONF_URL_SOURCE: URL_SOURCE_MDNS,
                        CONF_MDNS_LAST_UPDATE: discovered_at,
                    }
                    self.hass.config_entries.async_update_entry(
                        existing_entry,
                        data=updated_data,
                        options=updated_options,
                    )
            return self.async_abort(reason="already_configured")

        self.context["title_placeholders"] = {"name": device_name,}
        persistent_notification.async_create(
            self.hass,
            title="🔊 Phát hiện VBot Assistant",
            message=(
                f"Đã Tìm Thấy Thiết Bị: **{device_name}**\n\n"
                f"- Tên MQTT Client: `{device_id}`\n\n"
                f"- Địa Chỉ IP:API: `{url_api}`\n\n"
                f"- Phiên bản chương trình: `{device_version}`\n\n"
                f"👉 Vào **Cài đặt → Thiết bị & Dịch vụ → VBot Assistant** để thêm thiết bị này.\n\n"
                f"👉 [Nhấn vào đây để mở Thiết bị & Dịch vụ](/config/integrations)"
            ),
            notification_id=f"vbot_discovered_{device_id}",
        )
        #Nếu muốn button xác nhận
        return self.async_show_form(step_id="confirm", description_placeholders={"name": device_name, "version": device_version, "device": device_id, "host": url_api,},)

        #Tự động thêm khi scan thấy
        #return self.async_create_entry(title=f"{device_name} - {url_api.split(':')[0]} (MQTT: {device_id})", data={CONF_DEVICE_ID: device_id, VBot_URL_API: url_api, "name": device_name, "version": device_version,},)

    async def async_step_confirm(self, user_input=None):
        if user_input is None:
            device_name = (self._discovered_device.get("name") or "VBot Assistant").strip()
            device_version = (self._discovered_device.get("version") or "N/A").strip()
            device_id = self._discovered_device[CONF_DEVICE_ID]
            host = self._discovered_device[VBot_URL_API]
            return self.async_show_form(
                step_id="confirm",
                description_placeholders={
                    "name": device_name,
                    "version": device_version,
                    "device": device_id,
                    "host": host,
                },
            )
        device_id = self._discovered_device[CONF_DEVICE_ID]
        url_api = self._discovered_device[VBot_URL_API]
        device_name = (self._discovered_device.get("name") or "VBot Assistant").strip()
        #device_name = (getattr(self, "_discovered_device", {}).get("name") or "VBot Assistant").strip()
        device_version = (self._discovered_device.get("version") or "N/A").strip()
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured()
        persistent_notification.async_dismiss(self.hass, notification_id=f"vbot_discovered_{device_id}",)
        return self.async_create_entry(
            title=f"{device_name} - {urlsplit(url_api).hostname or url_api} (MQTT: {device_id})",
            data=self._discovered_device,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return VBotOptionsFlowHandler(config_entry)

#Giao diện Cấu hình lại
class VBotOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            auto_update = bool(user_input.get(CONF_AUTO_UPDATE_URL, False))
            return self.async_create_entry(
                title="",
                data={
                    VBot_URL_API: normalize_vbot_url(
                        user_input[VBot_URL_API],
                        self._config_entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_HOST),
                    ),
                    CONF_AUTO_UPDATE_URL: auto_update,
                    CONF_URL_SOURCE: URL_SOURCE_MDNS if auto_update else URL_SOURCE_MANUAL,
                },
            )
        current_url = self._config_entry.options.get(
            VBot_URL_API,
            self._config_entry.data.get(VBot_URL_API, "192.168.14.113:5002")
        )
        current_auto_update = self._config_entry.options.get(
            CONF_AUTO_UPDATE_URL,
            self._config_entry.data.get(
                CONF_AUTO_UPDATE_URL,
                self._config_entry.data.get(CONF_URL_SOURCE) == URL_SOURCE_MDNS,
            ),
        )
        schema = vol.Schema({
            vol.Required(VBot_URL_API, default=current_url): str,
            vol.Required(CONF_AUTO_UPDATE_URL, default=current_auto_update): bool,
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
