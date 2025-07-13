from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_DEVICE_ID

# Cấu trúc JSON-like để dễ thêm nhiều mục
def get_input_texts(device: str):
    device = device.lower()
    return {
        f"{device}_news_paper_name": {
            "name": "Nhập Tên Báo, Tin Tức"
        },
        f"{device}_main_processing": {
            "name": "Nội Dung Cần Xử Lý"
        },
        f"{device}_vbot_tts": {
            "name": "Nội Dung Thông Báo TTS"
        }
    }

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    #device = entry.data.get(CONF_DEVICE_ID, "VBot_DEV_UNKNOWN")
    device = entry.data[CONF_DEVICE_ID]
    input_texts_config = get_input_texts(device)
    entities = []

    for object_id, props in input_texts_config.items():
        entities.append(
            VBotInputText(
                object_id=object_id,
                name=props.get("name", object_id),
            )
        )

    async_add_entities(entities)


class VBotInputText(Entity):
    def __init__(self, object_id, name):
        self._attr_unique_id = object_id
        self._attr_name = name
        self._state = ""

    @property
    def state(self):
        return self._state

    async def async_set_state(self, value):
        self._state = value
        self.async_write_ha_state()

    async def async_update(self):
        pass
