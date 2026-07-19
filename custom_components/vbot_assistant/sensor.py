'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

import logging
import json
from homeassistant.components.sensor import SensorEntity
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
    sensors = [
        {
            "name": f"Ngày Phát Hành Giao Diện Sensor ({device})",
            "state_topic": f"{device}/sensor/vbot_interface_releaseDate/state",
            "icon": "mdi:calendar"
        },
        {
            "name": f"Phiên Bản Giao Diện Sensor ({device})",
            "state_topic": f"{device}/sensor/vbot_interface_version/state",
            "icon": "mdi:calendar"
        },
        {
            "name": f"Phiên Bản Chương Trình Sensor ({device})",
            "state_topic": f"{device}/sensor/vbot_program_version/state",
            "icon": "mdi:calendar"
        },
        {
            "name": f"Ngày Phát Hành Chương Trình Sensor ({device})",
            "state_topic": f"{device}/sensor/vbot_program_releaseDate/state",
            "icon": "mdi:calendar"
        },
    ]

    entities = [MQTTSensor(hass, device=device, **s) for s in sensors]
    entities.append(VBotTTSStateSensor(hass, device))
    async_add_entities(entities, update_before_add=True)

class MQTTSensor(SensorEntity):
    def __init__(self, hass, name, state_topic, icon=None, device=None):
        self._hass = hass
        self._name = name
        self._device = device
        self._attr_unique_id = f"{device.lower()}_{state_topic.replace('/', '_')}_sensor"
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


class VBotTTSStateSensor(MQTTSensor):
    def __init__(self, hass, device):
        super().__init__(
            hass,
            name=f"Trạng Thái TTS ({device})",
            state_topic=f"{device}/tts/state",
            icon="mdi:text-to-speech",
            device=device,
        )
        self._attributes = {}

    async def _message_received(self, msg):
        try:
            data = json.loads(msg.payload)
            if not isinstance(data, dict):
                raise ValueError("payload không phải object")
            self._state = str(data.get("state", "unknown"))
            self._attributes = {
                "text": data.get("text"),
                "source": data.get("source"),
                "error": data.get("error"),
                "updated_at": data.get("updated_at"),
            }
            self.async_write_ha_state()
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            _LOGGER.warning("Trạng thái TTS VBot không hợp lệ: %s", error)

    @property
    def extra_state_attributes(self):
        return self._attributes
