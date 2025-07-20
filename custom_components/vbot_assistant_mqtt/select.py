import logging
from homeassistant.components.select import SelectEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_DEVICE_ID

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

    # MQTT-based selects
    selects = [
        {
            "name": f"Kiểu Hiển Thị Logs Select ({device})",
            "state_topic": f"{device}/select/log_display_style/state",
            "command_topic": f"{device}/select/log_display_style/set",
            "options": ["console", "display_screen", "api", "all"],
            "icon": "mdi:math-log"
        }
    ]

    mqtt_entities = [MQTTSelect(hass, device=device, **s) for s in selects]
    internal_entities = [
        ProcessingModeSelect(device),
        ProcessingStreamSelect(device)
    ]
    async_add_entities(mqtt_entities + internal_entities, update_before_add=True)

# ✅ MQTT-based Select
class MQTTSelect(SelectEntity):
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
        await mqtt.async_subscribe(
            self._hass,
            self._state_topic,
            self._message_received,
            qos=1
        )

    async def _message_received(self, msg):
        payload = msg.payload
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
        await mqtt.async_publish(
            self._hass,
            self._command_topic,
            option,
            qos=1,
            retain=False
        )
        self._state = option
        self.async_write_ha_state()


# ✅ Internal Select: chế độ xử lý tác nhân
class ProcessingModeSelect(SelectEntity):
    def __init__(self, device):
        self._device = device
        self._attr_name = f"Assist Tác Nhân Chế Độ Xử Lý ({device})"
        self._attr_unique_id = f"{device.lower()}_assist_processing_mode_select"
        self._attr_options = ["chatbot", "processing"]
        self._attr_icon = "mdi:robot"
        self._attr_current_option = "chatbot"
        self._attr_entity_id = f"select.assist_processing_mode_select_{device.lower()}"
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

# ✅ Internal Select: luồng xử lý API hoặc MQTT
class ProcessingStreamSelect(SelectEntity):
    def __init__(self, device):
        self._device = device
        self._attr_name = f"Assist Tác Nhân Luồng Xử Lý ({device})"
        self._attr_unique_id = f"{device.lower()}_assist_stream_select"
        #self._attr_options = ["api", "mqtt"]
        self._attr_options = ["api"]
        self._attr_icon = "mdi:transfer-right"
        self._attr_current_option = "api"  # hoặc bạn chọn mặc định là "api"

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
