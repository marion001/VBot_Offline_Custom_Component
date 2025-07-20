import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from .const import DOMAIN, CONF_DEVICE_ID

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
            "template_input": f"text.{device.lower()}_news_paper_name"
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
        }
    ]

    entities = []
    for btn in buttons_config:
        entities.append(
            VBotMQTTButton(
                hass=hass,
                unique_id=btn["id"],
                name=btn["name"],
                topic=btn["topic"],
                payload=btn.get("payload"),
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
        topic: str,
        payload: str | None = None,
        template_input: str | None = None,
        icon: str = "mdi:gesture-tap-button",
        device: str | None = None
    ):
        self._hass = hass
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._topic = topic
        self._payload = payload
        self._template_input = template_input
        self._attr_icon = icon
        self._device = device

    async def async_press(self) -> None:
        payload = self._payload
        if self._template_input:
            state_obj = self._hass.states.get(self._template_input)
            if state_obj:
                payload = state_obj.state
            else:
                _LOGGER.warning("Không tìm thấy dữ liệu đầu vào mẫu: '%s'", self._template_input)
                return

        if payload is None:
            _LOGGER.warning("Không có nội dung nào để xuất bản cho nút: %s", self._attr_name)
            return

        _LOGGER.debug("Gửi tin nhắn MQTT tới %s: %s", self._topic, payload)
        await mqtt.async_publish(
            self._hass,
            self._topic,
            payload,
            qos=1,
            retain=True
        )

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
