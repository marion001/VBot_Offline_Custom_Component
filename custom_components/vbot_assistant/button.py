'''
Code By: Vũ Tuyển
GitHub VBot: https://github.com/marion001/VBot_Offline.git
Facebook Group: https://www.facebook.com/groups/1148385343358824
Facebook: https://www.facebook.com/TWFyaW9uMDAx
Mail: VBot.Assistant@gmail.com
'''

import logging
import json
from homeassistant.components.button import ButtonEntity
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN, CONF_DEVICE_ID, CONF_DEVICE_TYPE, DEVICE_TYPE_ANDROID

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities: AddEntitiesCallback, discovery_info: DiscoveryInfoType | None = None) -> None:
    #Không được sử dụng, khi sử dụng luồng cấu hình
    _LOGGER.warning("VBot Assistant MQTT không hỗ trợ cấu hình YAML. Vui lòng dùng UI (config_entry).")
    pass

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    cfg = entry.data
    device = cfg.get(CONF_DEVICE_ID)
    if not device:
        _LOGGER.error("Không tìm thấy Tên Client trong mục cấu hình")
        return

    buttons_config = [
        {
            "id": f"{device}_media_control_pause",
            "name": f"Media Pause Button ({device})",
            "icon": "mdi:pause-circle-outline",
            "topic": f"{device}/script/media_control/set",
            "payload": "PAUSE"
        },
        {
            "id": f"{device}_media_control_stop",
            "name": f"Media Stop Button ({device})",
            "icon": "mdi:stop-circle-outline",
            "topic": f"{device}/script/media_control/set",
            "payload": "STOP"
        },
        {
            "id": f"{device}_media_control_resume",
            "name": f"Media Resume Button ({device})",
            "icon": "mdi:motion-play-outline",
            "topic": f"{device}/script/media_control/set",
            "payload": "RESUME"
        },
        {
            "id": f"{device}_media_control_play",
            "name": f"Media Play Link URL Button ({device})",
            "icon": "mdi:motion-play",
            "topic": f"{device}/script/media_control/set",
            "template_input": f"text.vbot_play_music_link_url_{device.lower()}",
            "payload": "MEDIA_PLAY_DYNAMIC"
        },
        {
            "id": f"{device}_volume_control_up",
            "name": f"Volume UP Button ({device})",
            "icon": "mdi:volume-plus",
            "topic": f"{device}/script/volume_control/set",
            "payload": "UP"
        },
        {
            "id": f"{device}_volume_control_down",
            "name": f"{device} Volume DOWN Button",
            "icon": "mdi:volume-minus",
            "topic": f"{device}/script/volume_control/set",
            "payload": "DOWN"
        },
        {
            "id": f"{device}_volume_control_min",
            "name": f"Volume MIN Button ({device})",
            "icon": "mdi:volume-low",
            "topic": f"{device}/script/volume_control/set",
            "payload": "MIN"
        },
        {
            "id": f"{device}_volume_control_max",
            "name": f"Volume MAX Button ({device})",
            "icon": "mdi:volume-high",
            "topic": f"{device}/script/volume_control/set",
            "payload": "MAX"
        },
        {
            "id": f"{device}_playlist_local_player",
            "name": f"PlayList Local Player Button ({device})",
            "icon": "mdi:play",
            "topic": f"{device}/script/playlist_control/set",
            "payload": "LOCAL"
        },
        {
            "id": f"{device}_playlist_control_player",
            "name": f"PlayList Player Button ({device})",
            "icon": "mdi:play",
            "topic": f"{device}/script/playlist_control/set",
            "payload": "PLAY"
        },
        {
            "id": f"{device}_playlist_control_next",
            "name": f"PlayList Next Button ({device})",
            "icon": "mdi:skip-forward",
            "topic": f"{device}/script/playlist_control/set",
            "payload": "NEXT"
        },
        {
            "id": f"{device}_playlist_control_prev",
            "name": f"PlayList Prev Button ({device})",
            "icon": "mdi:skip-backward",
            "topic": f"{device}/script/playlist_control/set",
            "payload": "PREV"
        },
        {
            "id": f"{device}_news_paper_player",
            "name": f"News Paper Player Button ({device})",
            "icon": "mdi:podcast",
            "topic": f"{device}/script/news_paper/set",
            "template_input": f"text.news_paper_name_text_{device.lower()}"
        },
        {
            "id": f"{device}_main_processing",
            "name": f"Main Processing Button ({device})",
            "icon": "mdi:robot-confused-outline",
            "topic": f"{device}/script/main_processing/set",
            "template_input": f"text.main_processing_text_{device.lower()}"
        },
        {
            "id": f"{device}_vbot_tts",
            "name": f"VBot TTS Button ({device})",
            "icon": "mdi:robot-confused-outline",
            "topic": f"{device}/script/vbot_tts/set",
            "template_input": f"text.vbot_tts_text_{device.lower()}"
        },
        {
            "id": f"{device}_restart_vbot",
            "name": f"Restart VBot Button ({device})",
            "icon": "mdi:restart",
            "topic": f"{device}/script/power_action/set",
            "payload": "RESTART_VBOT_SERVICE"
        },
        {
            "id": f"{device}_stop_vbot",
            "name": f"Stop VBot Button ({device})",
            "icon": "mdi:power-off",
            "topic": f"{device}/script/power_action/set",
            "payload": "STOP_VBOT_SERRVICE"
        },
        {
            "id": f"{device}_reboot_system_os",
            "name": f"Reboot SYSTEM OS Button ({device})",
            "icon": "mdi:power-settings",
            "topic": f"{device}/script/power_action/set",
            "payload": "REBOOT_OS"
        },
        {
            "id": f"{device}_restart_interface",
            "name": f"Restart Giao Diện VBot Button ({device})",
            "icon": "mdi:restart",
            "topic": f"{device}/script/power_action/set",
            "payload": "RESTART_INTERFACE"
        },
        {
            "id": f"{device}_check_updates",
            "name": f"VBot Check Updates ({device})",
            "icon": "mdi:update",
            "command": "check_single_device_updates",
            "device_id": device
        }
    ]

    if entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_ANDROID:
        supported_payloads = {
            "PAUSE", "STOP", "RESUME", "MEDIA_PLAY_DYNAMIC",
            "UP", "DOWN", "MIN", "MAX", "LOCAL", "PLAY", "NEXT", "PREV",
            "RESTART_VBOT_SERVICE", "REBOOT_OS", "RESTART_INTERFACE",
        }
        buttons_config = [
            item for item in buttons_config
            if item.get("payload") in supported_payloads
            or item.get("topic", "").endswith("/script/vbot_tts/set")
        ]
        buttons_config.append({
            "id": f"{device}_bluetooth_pairing",
            "name": f"Mở Kết Nối Bluetooth ({device})",
            "icon": "mdi:bluetooth-connect",
            "topic": f"{device}/script/bluetooth_control/set",
            "payload": "PAIRING",
        })
        buttons_config.append({
            "id": f"{device}_bluetooth_disconnect",
            "name": f"Ngắt Kết Nối Bluetooth ({device})",
            "icon": "mdi:bluetooth-off",
            "topic": f"{device}/script/bluetooth_control/set",
            "payload": "DISCONNECT",
        })
    entities = []
    for btn in buttons_config:
        entities.append(
            VBotMQTTButton(
                hass=hass,
                unique_id=btn["id"],
                name=btn["name"],
                topic=btn.get("topic"),
                payload=btn.get("payload"),
                command=btn.get("command"),
                device_id=btn.get("device_id"),
                template_input=btn.get("template_input"),
                icon=btn.get("icon", "mdi:gesture-tap-button"),
                device=device
            )
        )
    async_add_entities(entities)

class VBotMQTTButton(ButtonEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        unique_id: str,
        name: str,
        topic: str | None = None,
        payload: str | None = None,
        command: str | None = None,
        device_id: str | None = None,
        template_input: str | None = None,
        icon: str = "mdi:gesture-tap-button",
        device: str | None = None
    ):
        self._hass = hass
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._topic = topic
        self._payload = payload
        self._command = command
        self._device_id = device_id
        self._template_input = template_input
        self._attr_icon = icon
        self._device = device

    async def async_press(self) -> None:
        if self._topic:
            payload = self._payload
            if self._template_input:
                state_obj = self._hass.states.get(self._template_input)
                if not state_obj and self._device:
                    registry = er.async_get(self._hass)
                    unique_suffix = "vbot_tts" if "vbot_tts" in self._template_input else (
                        "vbot_play_music_link_url" if "play_music" in self._template_input else None
                    )
                    if unique_suffix:
                        entity_id = registry.async_get_entity_id(
                            "text", DOMAIN, f"{self._device.lower()}_{unique_suffix}"
                        )
                        if entity_id:
                            state_obj = self._hass.states.get(entity_id)
                if not state_obj:
                    # Entity ID có thể đã được đổi trong giao diện HASS hoặc
                    # được tạo từ tên hiển thị thay vì unique_id.
                    candidates = (
                        f"text.vbot_tts_text_{self._device.lower()}"
                        if self._device and "vbot_tts" in (self._template_input or "")
                        else None,
                        f"text.news_paper_name_text_{self._device.lower()}"
                        if self._device and "news_paper" in (self._template_input or "")
                        else None,
                    )
                    for candidate in candidates:
                        if candidate:
                            state_obj = self._hass.states.get(candidate)
                            if state_obj:
                                break
                if not state_obj:
                    _LOGGER.warning("Không tìm thấy entity template_input: %s", self._template_input)
                    return
                value = state_obj.state
                #Nếu là media play → build JSON động
                if self._payload == "MEDIA_PLAY_DYNAMIC":
                    payload = json.dumps({"action": "play", "media_link": value, "media_name": "", "media_cover": "", "media_player_source": "MQTT"})
                else:
                    payload = value
            if payload is None:
                _LOGGER.warning("Không có payload cho nút: %s", self._attr_name)
                return
            # Command topics must not be retained: a reconnecting VBot must
            # never replay an old play/stop/power command.
            await mqtt.async_publish(self._hass, self._topic, payload, qos=1, retain=False)

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
