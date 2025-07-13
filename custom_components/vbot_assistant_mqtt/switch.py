import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    pass  # not used

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    cfg = entry.data
    device = cfg[CONF_DEVICE_ID]
    switches = [
        {
            "name": f"{device} Logs Hệ Thống",
            "state_topic": f"{device}/switch/log_display_active/state",
            "command_topic": f"{device}/switch/log_display_active/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
            "optimistic": False,
            "qos": 1,
            "retain": True,
        },
    ]
    ents = [MQTTSwitch(hass, **s) for s in switches]
    async_add_entities(ents, update_before_add=True)

class MQTTSwitch(SwitchEntity):
    def __init__(self, hass, name, state_topic, command_topic, payload_on, payload_off, state_on, state_off, optimistic, qos, retain):
        self._hass = hass
        self._name = name
        self._attr_unique_id = f"{state_topic}_switch"
        self._attr_device_class = "switch"
        self._state_topic = state_topic
        self._command_topic = command_topic
        self._payload_on = payload_on
        self._payload_off = payload_off
        self._state_on = state_on
        self._state_off = state_off
        self._optimistic = optimistic
        self._qos = qos
        self._retain = retain
        self._is_on = False

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
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        await mqtt.async_publish(self._hass, self._command_topic, self._payload_on, self._qos, self._retain)
        if self._optimistic:
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await mqtt.async_publish(self._hass, self._command_topic, self._payload_off, self._qos, self._retain)
        if self._optimistic:
            self._is_on = False
            self.async_write_ha_state()

    async def _message_received(self, msg):
        payload = msg.payload
        _LOGGER.debug(f"{self._name} MQTT recv: {payload}")
        self._is_on = payload == self._state_on
        self.async_write_ha_state()
