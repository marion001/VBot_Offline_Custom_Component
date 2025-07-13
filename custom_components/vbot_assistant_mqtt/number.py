import logging
import voluptuous as vol
from homeassistant.components.number import NumberEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    pass

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    device = entry.data[CONF_DEVICE_ID]
    numbers = [
        {
            "name": f"{device} Volume",
            "state_topic": f"{device}/number/volume/state",
            "command_topic": f"{device}/number/volume/set",
            "min_value": 0,
            "max_value": 100,
            "unit_of_measurement": "%",
            "qos": 1,
        },
        {
            "name": f"{device} Độ Sáng Đèn Led",
            "state_topic": f"{device}/number/led_brightness/state",
            "command_topic": f"{device}/number/led_brightness/set",
            "min_value": 0,
            "max_value": 255,
            "unit_of_measurement": None,
            "qos": 1,
        },
    ]
    ents = [MQTTNumber(hass, **n) for n in numbers]
    async_add_entities(ents, update_before_add=True)

class MQTTNumber(NumberEntity):
    def __init__(self, hass, name, state_topic, command_topic, min_value, max_value, qos, unit_of_measurement, icon=None):
        self._hass = hass
        self._name = name
        self._state_topic = state_topic
        self._command_topic = command_topic
        self._min_value = min_value
        self._max_value = max_value
        self._qos = qos
        self._unit = unit_of_measurement
        self._value = None
        #self._attr_icon = icon
        self._attr_icon = icon or "mdi:tune"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_unit_of_measurement = unit_of_measurement

    async def async_added_to_hass(self):
        await mqtt.async_subscribe(
            self._hass,
            self._state_topic,
            self._message_received,
            self._qos
        )

    @property
    def name(self):
        return self._name

    @property
    def native_value(self):
        return self._value

    async def async_set_native_value(self, value):
        await mqtt.async_publish(self._hass, self._command_topic, str(value), self._qos, False)
        self._value = value  # nếu optimistic
        self.async_write_ha_state()

    async def _message_received(self, msg):
        payload = msg.payload  # KHÔNG dùng .decode()
        try:
            self._value = float(payload)
            self.async_write_ha_state()
        except ValueError:
            _LOGGER.warning(f"Invalid payload for {self._name}: {payload}")
