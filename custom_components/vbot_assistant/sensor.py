import logging
import aiohttp
import json
from datetime import timedelta
from urllib.parse import urlparse
from homeassistant.components.sensor import SensorEntity
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_DEVICE_ID, VBot_URL_API

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    _LOGGER.warning("VBot Assistant MQTT không hỗ trợ cấu hình YAML. Vui lòng dùng UI (config_entry).")
    pass

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    cfg = entry.data
    device = cfg.get(CONF_DEVICE_ID)
    url_api = cfg.get(VBot_URL_API)
    if not device:
        _LOGGER.error("Không tìm thấy Tên Client trong mục cấu hình")
        return
    if not url_api:
        _LOGGER.error("Không tìm thấy URL API trong mục cấu hình")
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
            "icon": "mdi:information"
        },
        {
            "name": f"Phiên Bản Chương Trình Sensor ({device})",
            "state_topic": f"{device}/sensor/vbot_program_version/state",
            "icon": "mdi:information"
        },
        {
            "name": f"Ngày Phát Hành Chương Trình Sensor ({device})",
            "state_topic": f"{device}/sensor/vbot_program_releaseDate/state",
            "icon": "mdi:calendar"
        },
        {
            "name": f"Phiên Bản Giao Diện Mới ({device})",
            "state_topic": f"{device}/sensor/vbot_interface_new_version/state",
            "icon": "mdi:update",
            "check_new_version": True,
            "version_type": "interface",
            "url_api": url_api,
            "update_interval": 60  # Cập nhật mỗi 1 giờ
        },
        {
            "name": f"Phiên Bản Chương Trình Mới ({device})",
            "state_topic": f"{device}/sensor/vbot_program_new_version/state",
            "icon": "mdi:update",
            "check_new_version": True,
            "version_type": "program",
            "url_api": url_api,
            "update_interval": 60  # Cập nhật mỗi 1 giờ
        },
    ]

    entities = [MQTTSensor(hass, device=device, **s) for s in sensors]
    async_add_entities(entities, update_before_add=True)

class MQTTSensor(SensorEntity):
    def __init__(self, hass, name, state_topic, icon=None, device=None, check_new_version=False, version_type=None, url_api=None, update_interval=None):
        self._hass = hass
        self._name = name
        self._device = device
        self._attr_unique_id = f"{device.lower()}_{state_topic.replace('/', '_').replace(':', '_')}_sensor"
        self._state_topic = state_topic
        self._attr_icon = icon or "mdi:tune"
        self._attr_unit_of_measurement = None
        self._state = None
        self._check_new_version = check_new_version
        self._version_type = version_type
        self._url_api = url_api
        self._github_repo = "marion001/VBot_Offline"
        self._github_branch = "main"
        if update_interval:
            self._attr_update_interval = timedelta(seconds=update_interval)

    async def async_added_to_hass(self):
        if self._state_topic:
            await mqtt.async_subscribe(
                self._hass,
                self._state_topic,
                self._message_received,
                qos=1
            )

    async def _message_received(self, msg):
        payload = msg.payload
        if not payload:
            _LOGGER.warning(f"{self._name} nhận payload rỗng từ topic {self._state_topic}")
            return

        _LOGGER.debug(f"{self._name} MQTT nhận: {payload}")
        if self._check_new_version:
            self._state = await self._check_version_update(payload)
        else:
            self._state = payload
        self.async_write_ha_state()

    async def async_update(self):
        """Cập nhật trạng thái định kỳ cho sensor có update_interval."""
        if self._check_new_version:
            self._state = await self._check_version_update(None)
            self.async_write_ha_state()

    async def _check_version_update(self, local_version):
        """Kiểm tra xem có phiên bản mới trên GitHub hay không."""
        if not self._url_api:
            _LOGGER.error(f"Không có URL API cho {self._name}")
            return "Không"
        api_url = f"http://{self._url_api.split(':')[0]}/VBot_API.php"
        try:
            async with aiohttp.ClientSession() as session:
                # Lấy phiên bản từ API nội bộ
                async with session.get(api_url, timeout=5) as res:
                    if res.status != 200:
                        _LOGGER.error(f"Lỗi khi lấy dữ liệu từ API nội bộ: {res.status}")
                        return "Không"
                    data = await res.json()
                    local_version = data['version'][self._version_type]

                # Lấy phiên bản từ GitHub
                file_path = "Version.json" if self._version_type == "program" else "html/Version.json"
                github_url = f"https://api.github.com/repos/{self._github_repo}/contents/{file_path}?ref={self._github_branch}"
                headers = {"Accept": "application/vnd.github.v3.raw"}
                async with session.get(github_url, headers=headers, timeout=5) as res:
                    if res.status != 200:
                        _LOGGER.error(f"Lỗi khi lấy file {file_path} từ GitHub: {res.status}")
                        return "Không"
                    github_data = await res.json()
                    github_version = github_data.get('releaseDate')

                # So sánh phiên bản
                if github_version and local_version and github_version != local_version:
                    return "Có"
                return "Không"
        except Exception as e:
            _LOGGER.error(f"Lỗi khi kiểm tra phiên bản mới cho {self._name}: {e}")
            return "Không"

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