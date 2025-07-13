import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    pass

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    cfg = entry.data
    device = cfg.get(CONF_DEVICE_ID)
    if not device:
        _LOGGER.error("Không tìm thấy Tên Client trong mục cấu hình")
        return
    sensors = [
        {
            "name": f"{device} Ngày Phát Hành Giao Diện",
            "state_topic": f"{device}/sensor/vbot_interface_releaseDate/state",
            "icon": "mdi:calendar"
        },
        {
            "name": f"{device} Phiên Bản Giao Diện",
            "state_topic": f"{device}/sensor/vbot_interface_version/state",
            "icon": "mdi:calendar"
        },
        {
            "name": f"{device} Phiên Bản Chương Trình",
            "state_topic": f"{device}/sensor/vbot_program_version/state",
            "icon": "mdi:calendar"
        },
        {
            "name": f"{device} Ngày Phát Hành Chương Trình",
            "state_topic": f"{device}/sensor/vbot_program_releaseDate/state",
            "icon": "mdi:calendar"
        },
    ]

    entities = [MQTTSensor(hass, **s) for s in sensors]
    async_add_entities(entities, update_before_add=True)


class MQTTSensor(SensorEntity):
    def __init__(self, hass, name, state_topic, icon=None):
        self._hass = hass
        self._name = name
        self._state_topic = state_topic
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
    def state(self):
        return self._state
