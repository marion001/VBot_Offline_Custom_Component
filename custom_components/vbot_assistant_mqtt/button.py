import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    # Not used for config flow setup
    pass


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    cfg = entry.data
    device = cfg[CONF_DEVICE_ID]

    buttons_config = [
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
        # Bạn có thể thêm nhiều button hơn tại đây...
    ]

    entities = [
        VBotMQTTButton(
            hass=hass,
            unique_id=btn["id"],
            name=btn["name"],
            topic=btn["topic"],
            payload=btn.get("payload"),
            template_input=btn.get("template_input"),
            icon=btn.get("icon", "mdi:gesture-tap-button")
        )
        for btn in buttons_config
    ]

    async_add_entities(entities)


class VBotMQTTButton(ButtonEntity):
    def __init__(self, hass, unique_id, name, topic, payload=None, template_input=None, icon="mdi:gesture-tap-button"):
        self._hass = hass
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._topic = topic
        self._payload = payload
        self._template_input = template_input
        self._attr_icon = icon

    async def async_press(self):
        payload = self._payload
        if self._template_input:
            payload = self._hass.states.get(self._template_input)
            if payload:
                payload = payload.state
            else:
                _LOGGER.warning(f"Input text {self._template_input} not found.")
                return

        if payload is None:
            _LOGGER.warning(f"No payload found for button {self.name}")
            return

        _LOGGER.debug(f"Publishing to {self._topic}: {payload}")
        await mqtt.async_publish(self._hass, self._topic, payload, qos=1, retain=True)
