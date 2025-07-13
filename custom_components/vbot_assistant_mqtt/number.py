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
            "min": 0,
            "max": 100,
            "unit": "%",
            "qos": 1,
        },
        {
            "name": f"{device} Độ Sáng Đèn Led",
            "state_topic": f"{device}/number/led_brightness/state",
            "command_topic": f"{device}/number/led_brightness/set",
            "min": 0,
            "max": 255,
            "unit": None,
            "qos": 1,
        },
    ]
    ents = [MQTTNumber(hass, **n) for n in numbers]
    async_add_entities(ents, update_before_add=True)

class MQTTNumber(NumberEntity):
    def __init__(self, hass, name, state_topic, command_topic, min, max, unit, qos):
        self._hass = hass
        self._name = name
        self._state_topic = state_topic
        self._command_topic = command_topic
        self._min = min
        self._max = max
        self._unit = unit
        self._qos = qos
        self._value = None

        mqtt.async_subscribe(hass, self._state_topic, self._message_received, self._qos)

    @property
    def name(self):
        return self._name

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def min_value(self):
        return self._min

    @property
    def max_value(self):
        return self._max

    @property
    def value(self):
        return self._value

    async def async_set_value(self, value):
        await mqtt.async_publish(self._hass, self._command_topic, str(value), self._qos)
        self._value = value
        self.async_write_ha_state()

    async def _message_received(self, msg):
        try:
            val = float(msg.payload.decode())
            self._value = val
            self.async_write_ha_state()
        except ValueError:
            _LOGGER.warning(f"{self._name} received invalid value: {msg.payload}")
