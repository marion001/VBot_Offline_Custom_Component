import logging
from homeassistant.components.script import ScriptEntity
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, CONF_DEVICE_ID  # cần đảm bảo bạn có CONF_DEVICE_ID = "device"

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    device = entry.data[CONF_DEVICE_ID]

    def generate_scripts(device_id):
        return {
            f"{device_id}_media_control_stop": {
                "alias": f"{device_id} Media Stop",
                "icon": "mdi:stop-circle-outline",
                "sequence": [
                    {
                        "service": "mqtt.publish",
                        "data": {
                            "topic": f"{device_id}/script/media_control/set",
                            "payload": "STOP",
                            "qos": 1,
                            "retain": True
                        }
                    }
                ]
            },
            f"{device_id}_media_control_resume": {
                "alias": f"{device_id} Media Resume",
                "icon": "mdi:motion-play-outline",
                "sequence": [
                    {
                        "service": "mqtt.publish",
                        "data": {
                            "topic": f"{device_id}/script/media_control/set",
                            "payload": "RESUME",
                            "qos": 1,
                            "retain": True
                        }
                    }
                ]
            },
            f"{device_id}_vbot_tts": {
                "alias": f"{device_id} VBot TTS",
                "icon": "mdi:robot-confused-outline",
                "sequence": [
                    {
                        "service": "mqtt.publish",
                        "data": {
                            "topic": f"{device_id}/script/vbot_tts/set",
                            "payload_template": f"{{{{ states('input_text.{device_id.lower()}_vbot_tts') }}}}",
                            "qos": 1,
                            "retain": True
                        }
                    }
                ]
            }
        }

    # tạo script từ device
    SCRIPTS = generate_scripts(device)

    entities = []

    for script_id, cfg in SCRIPTS.items():
        name = cfg.get("alias", script_id)
        icon = cfg.get("icon")
        sequence = cfg.get("sequence", [])

        for step in sequence:
            service = step.get("service")
            data = step.get("data", {})
            topic = data.get("topic")
            payload = data.get("payload")
            payload_template = data.get("payload_template")
            qos = data.get("qos", 1)
            retain = data.get("retain", True)

            if service == "mqtt.publish" and payload_template:
                entities.append(
                    VBotMQTTScriptTemplate(hass, name, topic, payload_template, qos, retain, icon)
                )
            elif service == "mqtt.publish" and payload is not None:
                entities.append(
                    VBotMQTTScriptStatic(hass, name, topic, payload, qos, retain, icon)
                )

    async_add_entities(entities, update_before_add=False)

# ------- Class định nghĩa thực thể script --------

class VBotMQTTScriptStatic(ScriptEntity):
    def __init__(self, hass, name, topic, payload, qos, retain, icon=None):
        self._hass = hass
        self._name = name
        self._topic = topic
        self._payload = payload
        self._qos = qos
        self._retain = retain
        self._attr_icon = icon or "mdi:tune"
        self._attr_has_entity_name = True

    async def async_run(self, context=None):
        await mqtt.async_publish(self._hass, self._topic, self._payload, self._qos, self._retain)

    @property
    def name(self):
        return self._name

class VBotMQTTScriptTemplate(ScriptEntity):
    def __init__(self, hass, name, topic, template_str, qos, retain, icon=None):
        self._hass = hass
        self._name = name
        self._topic = topic
        self._template_str = template_str
        self._qos = qos
        self._retain = retain
        self._attr_icon = icon or "mdi:tune"
        self._attr_has_entity_name = True

    async def async_run(self, context=None):
        try:
            rendered = self._hass.helpers.template.Template(self._template_str, self._hass).async_render()
            await mqtt.async_publish(self._hass, self._topic, rendered, self._qos, self._retain)
        except Exception as e:
            _LOGGER.error(f"Error rendering template for {self._name}: {e}")

    @property
    def name(self):
        return self._name
