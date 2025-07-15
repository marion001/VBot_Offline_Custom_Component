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
    selects = [
        {
            "name": f"{device} Kiểu Hiển Thị Logs",
            "state_topic": f"{device}/select/log_display_style/state",
            "command_topic": f"{device}/select/log_display_style/set",
            "options": ["console", "display_screen", "api", "all"],
            "icon": "mdi:math-log"
        }
    ]

    entities = [MQTTSelect(hass, device=device, **s) for s in selects]
    async_add_entities(entities, update_before_add=True)


class MQTTSelect(SelectEntity):
    def __init__(self, hass, name, state_topic, command_topic, options, icon=None, device=None):
        self._hass = hass
        self._name = name
        self._device = device
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
