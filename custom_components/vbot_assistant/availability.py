"""Shared MQTT availability handling for VBot entities."""

from homeassistant.components import mqtt
from homeassistant.core import callback


class MQTTAvailabilityMixin:
    """Track explicit VBot online/offline messages without blocking startup."""

    # Older VBot versions did not publish an availability topic.  Keep entities
    # usable until the broker explicitly reports that the device is offline.
    _attr_available = True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if getattr(self, "_vbot_availability_exempt", False):
            self._attr_available = True
            return
        device = getattr(self, "_device", None)
        if not device:
            return
        unsubscribe = await mqtt.async_subscribe(
            self.hass,
            f"{device}/availability",
            self._handle_vbot_availability,
            qos=1,
        )
        self.async_on_remove(unsubscribe)

    @callback
    def _handle_vbot_availability(self, message) -> None:
        self._attr_available = str(message.payload).strip().lower() == "online"
        self.async_write_ha_state()
