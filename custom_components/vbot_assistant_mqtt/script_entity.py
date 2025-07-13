import logging
from homeassistant.helpers.entity import Entity
from homeassistant.components import mqtt

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    config = entry.data
    device = config.get("device_id", "VBot")
    
    scripts = [
        {
            "id": f"{device}_media_pause",
            "name": f"{device} Media Pause",
            "icon": "mdi:pause-circle-outline",
            "topic": f"{device}/script/media_control/set",
            "payload": "PAUSE"
        },
        {
            "id": f"{device}_media_stop",
            "name": f"{device} Media Stop",
            "icon": "mdi:stop-circle-outline",
            "topic": f"{device}/script/media_control/set",
            "payload": "STOP"
        },
        {
            "id": f"{device}_vbot_tts",
            "name": f"{device} VBot TTS",
            "icon": "mdi:robot",
            "topic": f"{device}/script/vbot_tts/set",
            "template_input": f"input_text.{device.lower()}_vbot_tts"
        },
        {
            "id": f"{device}_main_processing",
            "name": f"{device} Main Processing",
            "icon": "mdi:robot-confused-outline",
            "topic": f"{device}/script/main_processing/set",
            "template_input": f"input_text.{device.lower()}_main_processing"
        }
    ]

    entities = [MQTTScriptEntity(hass, script) for script in scripts]
    async_add_entities(entities)


class MQTTScriptEntity(Entity):
    def __init__(self, hass, config):
        self._hass = hass
        self._id = config["id"]
        self._attr_unique_id = config["id"]
        self._attr_name = config["name"]
        self._attr_icon = config.get("icon", "mdi:script")
        self._topic = config["topic"]
        self._payload = config.get("payload")
        self._input_text = config.get("template_input")

    async def async_turn_on(self, **kwargs):
        payload = self._payload
        if self._input_text:
            state_obj = self._hass.states.get(self._input_text)
            if state_obj:
                payload = state_obj.state

        if payload is not None:
            _LOGGER.debug(f"[{self._attr_name}] Publish to {self._topic}: {payload}")
            await mqtt.async_publish(self._hass, self._topic, payload, qos=1, retain=True)

    @property
    def should_poll(self):
        return False

    @property
    def available(self):
        return True
