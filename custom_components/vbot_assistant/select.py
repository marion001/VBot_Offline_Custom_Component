'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

import logging
import json
from homeassistant.components.select import SelectEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from .const import DOMAIN, CONF_DEVICE_ID, CONF_DEVICE_TYPE, DEVICE_TYPE_HOST
from .availability import MQTTAvailabilityMixin

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    _LOGGER.warning("VBot Assistant MQTT không hỗ trợ cấu hình YAML. Vui lòng dùng UI (config_entry).")
    pass

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    cfg = entry.data
    device = cfg.get(CONF_DEVICE_ID)
    if not device:
        _LOGGER.error("Không tìm thấy Tên Client trong mục cấu hình")
        return

    selects = [
        {
            "name": f"Kiểu Hiển Thị Logs Select ({device})",
            "state_topic": f"{device}/select/log_display_style/state",
            "command_topic": f"{device}/select/log_display_style/set",
            "options": ["console", "dev_custom", "api", "all"],
            "icon": "mdi:math-log"
        }
    ]

    mqtt_entities = [MQTTSelect(hass, device=device, **s) for s in selects]
    internal_entities = [
        ProcessingModeSelect(device),
        ProcessingStreamSelect(device)
    ]
    if cfg.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_HOST:
        internal_entities.extend([
            VBotDynamicMQTTSelect(
                hass, device, "PlayList Được Chọn", f"{device}/playlist/state",
                "playlists", "current_id", "default_id", "mdi:playlist-music",
                f"{device.lower()}_playlist_selected",
            ),
            VBotDynamicMQTTSelect(
                hass, device, "Nhóm Multiroom Được Chọn", f"{device}/multiroom/state",
                "groups", "group_id", None, "mdi:speaker-multiple",
                f"{device.lower()}_multiroom_group_selected",
            ),
        ])
    async_add_entities(mqtt_entities + internal_entities, update_before_add=True)

class MQTTSelect(MQTTAvailabilityMixin, SelectEntity):
    def __init__(self, hass, name, state_topic, command_topic, options, icon=None, device=None):
        self._hass = hass
        self._name = name
        self._device = device
        self._attr_unique_id = f"{device.lower()}_{state_topic.replace('/', '_')}_select"
        self._state_topic = state_topic
        self._command_topic = command_topic
        self._options = options
        self._attr_icon = icon or "mdi:tune"
        self._state = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        unsubscribe = await mqtt.async_subscribe(
            self._hass,
            self._state_topic,
            self._message_received,
            qos=1
        )
        self.async_on_remove(unsubscribe)

    async def _message_received(self, msg):
        payload = msg.payload
        if payload not in self._options:
            _LOGGER.warning("Giá trị select không hợp lệ cho %s: %s", self._name, payload)
            return
        _LOGGER.debug(f"{self._name} MQTT nhận: {payload}")
        self._state = payload
        self.async_write_ha_state()

    @property
    def name(self):
        return self._name

    @property
    def options(self):
        return self._options

    @property
    def current_option(self):
        return self._state

    @property
    def device_info(self):
        if not self._device:
            return None
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT"
        }

    async def async_select_option(self, option):
        if option not in self._options:
            raise ValueError(f"Tùy chọn không hợp lệ: {option}")
        await mqtt.async_publish(self._hass, self._command_topic, option, qos=1, retain=False)
        self._state = option
        self.async_write_ha_state()

class VBotDynamicMQTTSelect(MQTTAvailabilityMixin, SelectEntity):
    """Select động lấy danh sách id/tên từ snapshot MQTT retained của VBot."""

    def __init__(self, hass, device, name, state_topic, list_key, current_key, fallback_key, icon, unique_id):
        self._hass = hass
        self._device = device
        self._attr_name = f"{name} ({device})"
        self._attr_unique_id = unique_id
        self._attr_icon = icon
        self._state_topic = state_topic
        self._list_key = list_key
        self._current_key = current_key
        self._fallback_key = fallback_key
        self._attr_options = []
        self._attr_current_option = None
        self._id_by_option = {}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        unsubscribe = await mqtt.async_subscribe(self._hass, self._state_topic, self._message_received, qos=1)
        self.async_on_remove(unsubscribe)

    @callback
    def _message_received(self, message):
        try:
            payload = json.loads(message.payload)
            rows = payload.get(self._list_key, [])
            mapping = {}
            for row in rows:
                item_id = str(row.get("id") or "").strip()
                if not item_id:
                    continue
                label = str(row.get("name") or item_id).strip()
                if label in mapping:
                    label = f"{label} ({item_id})"
                mapping[label] = item_id
            previous_id = self.selected_id
            self._id_by_option = mapping
            self._attr_options = list(mapping)
            preferred_id = previous_id or str(payload.get(self._current_key) or "").strip()
            if not preferred_id and self._fallback_key:
                preferred_id = str(payload.get(self._fallback_key) or "").strip()
            self._attr_current_option = next((label for label, item_id in mapping.items() if item_id == preferred_id), None)
            if self._attr_current_option is None and self._attr_options:
                self._attr_current_option = self._attr_options[0]
            self.async_write_ha_state()
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            _LOGGER.warning("Snapshot select động VBot không hợp lệ: %s", error)

    @property
    def selected_id(self):
        return self._id_by_option.get(self._attr_current_option)

    async def async_select_option(self, option):
        if option not in self._id_by_option:
            raise ValueError(f"Tùy chọn không hợp lệ: {option}")
        self._attr_current_option = option
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        return {"selected_id": self.selected_id, "items": dict(self._id_by_option)}

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT",
        }

#Chế độ cho tác Nhân VBot Assist xử lý
class ProcessingModeSelect(SelectEntity):
    def __init__(self, device):
        self._device = device
        self._attr_name = f"Assist Tác Nhân Chế Độ Xử Lý ({device})"
        self._attr_unique_id = f"{device.lower()}_assist_processing_mode_select"
        self._attr_options = ["chatbot", "processing"]
        self._attr_icon = "mdi:robot"
        self._attr_current_option = "chatbot"
        self._attr_entity_id = f"select.assist_tac_nhan_che_do_xu_ly_{device.lower()}"
    @property
    def current_option(self):
        return self._attr_current_option

    async def async_select_option(self, option: str):
        self._attr_current_option = option
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT"
        }

#Lựa Chọn luồng xử lý API hoặc MQTT
class ProcessingStreamSelect(SelectEntity):
    def __init__(self, device):
        self._device = device
        self._attr_name = f"Assist Tác Nhân Luồng Xử Lý ({device})"
        self._attr_unique_id = f"{device.lower()}_assist_stream_select"
        #self._attr_options = ["api", "mqtt"]
        self._attr_options = ["api"]
        self._attr_icon = "mdi:transfer-right"
        #Mặc Định chọn API
        self._attr_current_option = "api"
        self._attr_entity_id = f"select.assist_tac_nhan_luong_xu_ly_{device.lower()}"

    @property
    def current_option(self):
        return self._attr_current_option

    async def async_select_option(self, option: str):
        self._attr_current_option = option
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT"
        }
