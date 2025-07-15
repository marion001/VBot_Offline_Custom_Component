import logging
from homeassistant.components.text import TextEntity  # ✅ Sửa ở đây
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    cfg = entry.data
    device = cfg.get(CONF_DEVICE_ID)
    if not device:
        _LOGGER.error("Không tìm thấy Tên Client trong mục cấu hình")
        return

    # Danh sách text field cấu hình động
    inputs_config = [
        {
            "id": f"{device.lower()}_news_paper_name",
            "name": f"{device} News Paper Name",
        },
        {
            "id": f"{device.lower()}_main_processing",
            "name": f"{device} Main Processing",
        },
        {
            "id": f"{device.lower()}_vbot_tts",
            "name": f"{device} VBot TTS",
        }
    ]

    entities = []
    for inp in inputs_config:
        entities.append(
            VBotTextEntity(
                unique_id=inp["id"],
                #name=inp["name"],
                name=inp["id"],
                device=device,
            )
        )

    async_add_entities(entities)

class VBotTextEntity(TextEntity):  # ✅ Kế thừa TextEntity thay vì InputTextEntity
    def __init__(self, unique_id: str, name: str, device: str):
        self._attr_unique_id = unique_id
        self._attr_name = name  # tên thân thiện
        self._device = device
        self._attr_native_value = ""
        self._attr_min = 0
        self._attr_max = 255

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT",
        }

    @property
    def native_value(self) -> str:
        return self._attr_native_value

    async def async_set_value(self, value: str) -> None:
        _LOGGER.debug("Thiết lập giá trị của %s thành %s", self._attr_unique_id, value)
        self._attr_native_value = value
        self.async_write_ha_state()
        # Optional: publish MQTT ở đây nếu cần
