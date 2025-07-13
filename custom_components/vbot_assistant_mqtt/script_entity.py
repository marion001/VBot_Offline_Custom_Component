from homeassistant.components.button import ButtonEntity
from homeassistant.components.mqtt import async_publish
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    device = entry.data.get("device_id", "UNKNOWN_DEVICE")

    scripts = [
        {
            "id": f"{device}_media_pause",
            "name": f"{device} Media Pause",
            "icon": "mdi:pause-circle-outline",
            "topic": f"{device}/script/media_control/set",
            "payload": "PAUSE"
        },
        {
            "id": f"{device}_vbot_tts",
            "name": f"{device} VBot TTS",
            "icon": "mdi:robot",
            "topic": f"{device}/script/vbot_tts/set",
            "template_input": f"input_text.{device.lower()}_vbot_tts"
        },
    ]

    entities = [VBotScriptButton(hass, **conf) for conf in scripts]
    async_add_entities(entities)

class VBotScriptButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, id, name, icon, topic, payload=None, template_input=None):
        self._hass = hass
        self._attr_unique_id = id
        self._attr_name = name
        self._attr_icon = icon
        self._topic = topic
        self._payload = payload
        self._template_input = template_input

    async def async_press(self) -> None:
        payload = self._payload
        if self._template_input:
            state = self._hass.states.get(self._template_input)
            payload = state.state if state else ""

        await async_publish(
            self._hass,
            self._topic,
            payload,
            qos=1,
            retain=True
        )
