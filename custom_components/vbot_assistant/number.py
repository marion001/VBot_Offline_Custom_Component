'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

import logging
import math
import json
import voluptuous as vol
from homeassistant.components.number import NumberEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from .const import DOMAIN, CONF_DEVICE_ID, CONF_DEVICE_TYPE, DEVICE_TYPE_HOST, DEVICE_TYPE_ESP32
from .availability import MQTTAvailabilityMixin

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    _LOGGER.warning("VBot Assistant MQTT không hỗ trợ cấu hình YAML. Vui lòng dùng UI (config_entry).")
    pass

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    runtime = entry.runtime_data
    device = runtime.device_id
    if not device:
        _LOGGER.error("Không tìm thấy Tên Client trong mục cấu hình")
        return
    numbers = [
        {
            "name": f"Volume Slide ({device})",
            "state_topic": f"{device}/number/volume/state",
            "command_topic": f"{device}/number/volume/set",
            "min_value": 0,
            "max_value": 100,
            "unit_of_measurement": "%",
            "icon": "mdi:volume-source",
            "qos": 1,
        },
    ]
    if runtime.device_type in (DEVICE_TYPE_HOST, DEVICE_TYPE_ESP32):
        numbers.append({
            "name": f"Độ Sáng Đèn Led Slide ({device})",
            "state_topic": f"{device}/number/led_brightness/state",
            "command_topic": f"{device}/number/led_brightness/set",
            "min_value": 0,
            "max_value": 100,
            "unit_of_measurement": None,
            "icon": "mdi:brightness-5",
            "qos": 1,
        })
    ents = [MQTTNumber(hass, device=device, **n) for n in numbers]
    if runtime.device_type == DEVICE_TYPE_HOST:
        ents.extend(VBotEqualizerNumber(hass,device,key,label,minimum,maximum,step,unit)
                    for key,label,minimum,maximum,step,unit in EQ_FIELDS)
    async_add_entities(ents, update_before_add=True)


EQ_FIELDS = (
    ('bass_db','EQ Bass 100 Hz',-12,12,0.5,'dB'),
    ('low_mid_db','EQ Low Mid 250 Hz',-12,12,0.5,'dB'),
    ('mid_db','EQ Mid 630 Hz',-12,12,0.5,'dB'),
    ('high_mid_db','EQ Presence 1.6 kHz',-12,12,0.5,'dB'),
    ('treble_db','EQ Treble 4 kHz',-12,12,0.5,'dB'),
    ('air_db','EQ Air 10 kHz',-12,12,0.5,'dB'),
    ('preamp_db','EQ Preamp',-12,0,0.5,'dB'),
    ('wet_percent','EQ Wet/Dry',0,100,1,'%'),
)


class VBotEqualizerNumber(MQTTAvailabilityMixin, NumberEntity):
    _attr_icon='mdi:equalizer'

    def __init__(self,hass,device,key,label,minimum,maximum,step,unit):
        self._hass,self._device,self._key=hass,device,key
        self._attr_name=f'{label} ({device})'
        self._attr_unique_id=f'{device.lower()}_equalizer_{key}'
        self._attr_native_min_value=minimum
        self._attr_native_max_value=maximum
        self._attr_native_step=step
        self._attr_native_unit_of_measurement=unit
        self._attr_native_value=None

    @property
    def available(self):
        return super().available and self._attr_native_value is not None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        unsubscribe=await mqtt.async_subscribe(self._hass,f'{self._device}/equalizer/state',self._message_received,qos=1)
        self.async_on_remove(unsubscribe)

    @callback
    def _message_received(self,message):
        try:
            data=json.loads(message.payload)
            if not isinstance(data,dict) or data.get('success') is not True:return
            value=data['state']['current'][self._key]
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):return
            if not self._attr_native_min_value<=value<=self._attr_native_max_value:return
            self._attr_native_value=value
            self._attr_extra_state_attributes={'eq_field':self._key,'eq_active':data.get('active')}
            self.async_write_ha_state()
        except (ValueError,TypeError,KeyError):
            _LOGGER.debug('Snapshot EQ không hợp lệ cho %s',self._device)

    async def async_set_native_value(self,value):
        if isinstance(value,bool):raise ValueError('Giá trị EQ không hợp lệ')
        numeric=float(value)
        if not math.isfinite(numeric) or not self._attr_native_min_value<=numeric<=self._attr_native_max_value:
            raise ValueError('Giá trị EQ ngoài giới hạn')
        numeric=round(numeric/self._attr_native_step)*self._attr_native_step
        await mqtt.async_publish(self._hass,f'{self._device}/script/equalizer_control/set',
                                 json.dumps({'action':'apply','bands':{self._key:numeric}}),qos=1,retain=False)

class MQTTNumber(MQTTAvailabilityMixin, NumberEntity):
    def __init__(self, hass, name, state_topic, command_topic, min_value, max_value, qos, unit_of_measurement, icon=None, device=None):
        self._hass = hass
        self._name = name
        self._device = device
        self._attr_unique_id = f"{device.lower()}_{state_topic.replace('/', '_')}_number"
        self._state_topic = state_topic
        self._command_topic = command_topic
        self._min_value = min_value
        self._max_value = max_value
        self._qos = qos
        self._unit = unit_of_measurement
        self._value = None
        self._attr_icon = icon or "mdi:tune"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = unit_of_measurement

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        unsubscribe = await mqtt.async_subscribe(
            self._hass,
            self._state_topic,
            self._message_received,
            self._qos
        )
        self.async_on_remove(unsubscribe)

    @property
    def name(self):
        return self._name

    @property
    def native_value(self):
        return self._value

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT"
        }

    async def async_set_native_value(self, value):
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError('Number must be finite')
        normalized = int(round(max(self._min_value, min(self._max_value, numeric))))
        await mqtt.async_publish(
            self._hass,
            self._command_topic,
            str(normalized),
            self._qos,
            False,
        )
        self._value = normalized
        self.async_write_ha_state()

    async def _message_received(self, msg):
        payload = msg.payload
        try:
            numeric = float(payload)
            if not math.isfinite(numeric) or not self._min_value <= numeric <= self._max_value:
                raise ValueError('Number is outside the valid range')
            self._value = numeric
            self.async_write_ha_state()
        except (TypeError, ValueError, OverflowError):
            _LOGGER.warning(f"Tải dữ liệu không hợp lệ cho {self._name}: {payload}")
