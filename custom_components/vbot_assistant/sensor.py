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
from homeassistant.helpers.entity import EntityCategory
from .const import (
    DOMAIN, CONF_DEVICE_ID, CONF_DEVICE_TYPE, VBot_URL_API,
    CONF_URL_SOURCE, CONF_MDNS_LAST_UPDATE, URL_SOURCE_MDNS,
    DEVICE_TYPE_ANDROID, DEVICE_TYPE_ESP32, normalize_vbot_url,
)
from .availability import MQTTAvailabilityMixin

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

    if entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_ESP32:
        sensor_specs = [
            ("Trạng Thái Kết Nối MQTT", "mqtt_connection", "mdi:access-point-network"),
            ("Phiên Bản", "version", "mdi:tag"),
            ("Tên Ứng Dụng", "application_name", "mdi:application"),
            ("Loại Bo Mạch", "package_name", "mdi:chip"),
            ("Tên WiFi", "wifi_name", "mdi:wifi"),
            ("Địa Chỉ IP", "ip_address", "mdi:ip-network"),
            ("Tên Client", "client_name", "mdi:speaker"),
            ("Tên Client MQTT", "mqtt_client_name", "mdi:message-processing"),
            ("Trạng Thái Kết Nối Máy Chủ", "server_connection", "mdi:server-network"),
            ("Máy Chủ Đang Kết Nối", "server_address", "mdi:server"),
            ("Trạng Thái Loa", "speaker_status", "mdi:speaker-message"),
            ("Trạng Thái mDNS", "mdns_status", "mdi:lan-connect"),
        ]
        sensors = [{
            "name": f"{label} ({device})",
            "state_topic": (
                f"{device}/availability"
                if topic == "mqtt_connection"
                else f"{device}/sensor/{topic}/state"
            ),
            "icon": icon,
        } for label, topic, icon in sensor_specs]
    elif entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_ANDROID:
        sensor_specs = [
            ("Thiết Bị Bluetooth Đang Kết Nối", "bluetooth_device_name", "mdi:bluetooth-audio"),
            ("Phiên Bản", "version", "mdi:tag"),
            ("Tên Ứng Dụng", "application_name", "mdi:application"),
            ("App", "app", "mdi:apps"),
            ("Tên App Package", "package_name", "mdi:package-variant"),
            ("Thời Gian Khởi Động", "started_at", "mdi:clock-start"),
            ("Tên WiFi", "wifi_name", "mdi:wifi"),
            ("Địa Chỉ IP", "ip_address", "mdi:ip-network"),
            ("Lựa Chọn Máy Chủ Kết Nối", "server_source", "mdi:server-network"),
            ("Tên Client", "client_name", "mdi:speaker"),
            ("Tên Client MQTT", "mqtt_client_name", "mdi:message-processing"),
            ("Trạng Thái Kết Nối Máy Chủ", "server_connection", "mdi:server-network"),
            ("Trạng Thái Loa", "speaker_status", "mdi:speaker-message"),
            ("Chế Độ Đánh Thức", "wakeword_mode", "mdi:account-voice"),
            ("Chế Độ Phát Playlist", "playlist_order", "mdi:playlist-music"),
            ("Trạng Thái mDNS", "mdns_status", "mdi:lan-connect"),
            ("Nguồn Phát Thực Tế", "playback_source", "mdi:audio-input-stereo-minijack"),
            ("Trạng Thái Kết Nối Bluetooth", "bluetooth_connection", "mdi:bluetooth-connect"),
        ]
        sensors = [
            {
                "name": f"{label} ({device})",
                "state_topic": f"{device}/sensor/{topic}/state",
                "icon": icon,
            }
            for label, topic, icon in sensor_specs
        ]
    else:
        host_sensor_specs = [
            # Trạng thái chung của loa chủ
            ("Trạng Thái Kết Nối MQTT", "mqtt_connection", "mdi:access-point-network"),
            ("Trạng Thái Loa", "speaker_status", "mdi:speaker-message"),
            ("Nguồn Phát Thực Tế", "playback_source", "mdi:audio-input-stereo-minijack"),
            ("Thời Gian Khởi Động", "started_at", "mdi:clock-start"),
            ("Tên WiFi", "wifi_name", "mdi:wifi"),
            ("Địa Chỉ IP", "ip_address", "mdi:ip-network"),
            ("Chế Độ Đánh Thức", "wakeword_mode", "mdi:account-voice"),
            ("Trạng Thái mDNS", "mdns_status", "mdi:lan-connect"),
            # Bluetooth
            ("Trạng Thái Bluetooth", "bluetooth_enabled", "mdi:bluetooth"),
            ("Phiên Bản Bluetooth", "bluetooth_version", "mdi:bluetooth"),
            ("Trạng Thái Kết Nối Bluetooth", "bluetooth_connection", "mdi:bluetooth-connect"),
            ("Thiết Bị Bluetooth Đang Kết Nối", "bluetooth_device_name", "mdi:bluetooth-audio"),
            ("Địa Chỉ MAC Bluetooth", "bluetooth_device_mac", "mdi:identifier"),
            ("Bluetooth Đang Phát", "bluetooth_playing", "mdi:bluetooth-audio"),
            ("Trạng Thái Âm Thanh Bluetooth", "bluetooth_audio", "mdi:volume-high"),
            ("Tên Bài Bluetooth", "bluetooth_title", "mdi:music"),
            ("Nghệ Sĩ Bluetooth", "bluetooth_artist", "mdi:account-music"),
            ("Album Bluetooth", "bluetooth_album", "mdi:album"),
            ("Thời Lượng Bluetooth", "bluetooth_duration", "mdi:timer-music"),
            ("Số Thiết Bị Bluetooth Kết Nối", "bluetooth_device_count", "mdi:counter"),
            # AirPlay / Shairport
            ("Trạng Thái Dịch Vụ AirPlay", "airplay_service", "mdi:cast-audio"),
            ("Phiên Bản AirPlay", "airplay_version", "mdi:airplay"),
            ("AirPlay Đang Phát", "airplay_playing", "mdi:airplay"),
            ("Tên Bài AirPlay", "airplay_title", "mdi:music"),
            ("Trạng Thái Âm Thanh AirPlay", "airplay_audio", "mdi:volume-high"),
            ("Trạng Thái Kết Nối Lại AirPlay", "airplay_reconnecting", "mdi:connection"),
        ]
        sensors.extend(
            {
                "name": f"{label} ({device})",
                "state_topic": (
                    f"{device}/availability"
                    if topic == "mqtt_connection"
                    else f"{device}/sensor/{topic}/state"
                ),
                "icon": icon,
            }
            for label, topic, icon in host_sensor_specs
        )
    entities = [MQTTSensor(hass, device=device, **s) for s in sensors]
    entities.append(VBotTTSStateSensor(hass, device))
    device_type = entry.data.get(CONF_DEVICE_TYPE)
    current_url = normalize_vbot_url(
        entry.options.get(VBot_URL_API, entry.data.get(VBot_URL_API, "")),
        device_type,
    )
    url_source = entry.options.get(
        CONF_URL_SOURCE,
        entry.data.get(CONF_URL_SOURCE, "manual"),
    )
    last_mdns_update = entry.options.get(
        CONF_MDNS_LAST_UPDATE,
        entry.data.get(CONF_MDNS_LAST_UPDATE, "Chưa cập nhật"),
    )
    entities.extend([
        VBotConfigDiagnosticSensor(
            device, "URL API Hiện Tại", "api_url", current_url, "mdi:web"
        ),
        VBotConfigDiagnosticSensor(
            device,
            "Nguồn URL API",
            "api_url_source",
            "mDNS" if url_source == URL_SOURCE_MDNS else "Thủ công",
            "mdi:source-branch",
        ),
        VBotConfigDiagnosticSensor(
            device,
            "Lần Cập Nhật URL Qua mDNS",
            "api_url_mdns_updated",
            last_mdns_update or "Chưa cập nhật",
            "mdi:clock-check-outline",
        ),
    ])
    async_add_entities(entities, update_before_add=True)


class VBotConfigDiagnosticSensor(SensorEntity):
    """Expose URL configuration diagnostics without extra MQTT traffic."""

    def __init__(self, device, label, key, value, icon):
        self._device = device
        self._attr_name = f"{label} ({device})"
        self._attr_unique_id = f"{device.lower()}_{key}_diagnostic"
        self._attr_native_value = value
        self._attr_icon = icon
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT",
        }

class MQTTSensor(MQTTAvailabilityMixin, SensorEntity):
    def __init__(self, hass, name, state_topic, icon=None, device=None):
        self._hass = hass
        self._name = name
        self._device = device
        self._attr_unique_id = f"{device.lower()}_{state_topic.replace('/', '_')}_sensor"
        self._state_topic = state_topic
        self._vbot_availability_exempt = state_topic.endswith("/availability")
        self._attr_icon = icon or "mdi:tune"
        self._state = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        unsubscribe = await mqtt.async_subscribe(
            self._hass,
            self._state_topic,
            self._message_received,
            qos=1
        )
        self.async_on_remove(unsubscribe)

    async def _message_received(self, msg):
        payload = msg.payload
        if self._state_topic.endswith("/availability"):
            availability = str(payload).strip().lower()
            if availability in {"online", "offline"}:
                payload = "Đã kết nối" if availability == "online" else "Mất kết nối"
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
