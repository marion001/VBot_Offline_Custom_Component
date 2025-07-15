import logging
from homeassistant.components.input_text import InputTextEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    cfg = entry.data
    device = cfg.get(CONF_DEVICE_ID)
    if not device:
        _LOGGER.error("Không tìm thấy Tên Client trong mục cấu hình")
        return

    inputs_config = [
        {
            "id": f"{device}_news_paper_name",
            "name": "Nhập Tên Báo, Tin Tức",
        },
        {
            "id": f"{device}_main_processing",
            "name": "Nội Dung Cần Xử Lý",
        },
        {
            "id": f"{device}_vbot_tts",
            "name": "Nội Dung Thông Báo TTS",
        }
    ]

    entities = []
    for inp in inputs_config:
        entities.append(
            VBotInputTextEntity(
                unique_id=inp["id"],
                name=inp["name"],
                device=device,
            )
        )

    async_add_entities(entities)

class VBotInputTextEntity(InputTextEntity):
    def __init__(self, unique_id: str, name: str, device: str):
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._device = device
        self._attr_native_value = ""

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": self._device,
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT",
        }

    async def async_set_value(self, value: str) -> None:
        _LOGGER.debug("Thiết lập giá trị của %s thành %s", self._attr_unique_id, value)
        self._attr_native_value = value
        self.async_write_ha_state()
