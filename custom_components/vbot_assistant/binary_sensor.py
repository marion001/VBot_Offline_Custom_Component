"""Binary sensors for boolean VBot states."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .availability import MQTTAvailabilityMixin, set_vbot_device_online
from .const import DEVICE_TYPE_ANDROID, DEVICE_TYPE_HOST


@dataclass(frozen=True, kw_only=True)
class VBotBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a boolean MQTT state."""

    topic_suffix: str
    payload_on: frozenset[str]
    availability_exempt: bool = False


DESCRIPTIONS = (
    VBotBinarySensorDescription(
        key="mqtt_connected",
        translation_key="mqtt_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        topic_suffix="availability",
        payload_on=frozenset({"online", "connected", "ready"}),
        availability_exempt=True,
    ),
    VBotBinarySensorDescription(
        key="microphone",
        translation_key="microphone",
        icon="mdi:microphone",
        topic_suffix="switch/mic_on_off/state",
        payload_on=frozenset({"on", "true", "1", "enabled"}),
    ),
    VBotBinarySensorDescription(
        key="bluetooth_connected",
        translation_key="bluetooth_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        topic_suffix="sensor/bluetooth_connection/state",
        payload_on=frozenset({"connected", "online", "on", "true", "1"}),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up supported VBot binary sensors."""
    runtime = entry.runtime_data
    descriptions = list(DESCRIPTIONS[:2])
    if runtime.device_type in (DEVICE_TYPE_HOST, DEVICE_TYPE_ANDROID):
        descriptions.append(DESCRIPTIONS[2])
    async_add_entities(
        VBotBinarySensor(hass, runtime.device_id, description)
        for description in descriptions
    )


class VBotBinarySensor(MQTTAvailabilityMixin, BinarySensorEntity):
    """Represent a retained boolean VBot MQTT state."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(self, hass, device: str, description: VBotBinarySensorDescription):
        self._hass = hass
        self._device = device
        self.entity_description = description
        self._attr_unique_id = f"{device.casefold()}_{description.key}_binary_sensor"
        self._vbot_availability_exempt = description.availability_exempt
        self._topic = f"{device}/{description.topic_suffix}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        unsubscribe = await mqtt.async_subscribe(
            self._hass, self._topic, self._handle_message, qos=1
        )
        self.async_on_remove(unsubscribe)

    @callback
    def _handle_message(self, message) -> None:
        value = str(message.payload or "").strip().casefold()
        self._attr_is_on = value in self.entity_description.payload_on
        if self.entity_description.availability_exempt:
            set_vbot_device_online(self.hass, self._device, self._attr_is_on)
        self.async_write_ha_state()
