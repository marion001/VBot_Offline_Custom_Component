"""MQTT-controlled RGB light for the host VBot LED strip."""

from __future__ import annotations

import json
import asyncio
import logging

from homeassistant.components import mqtt
from homeassistant.components.light import ColorMode, LightEntity, LightEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .availability import MQTTAvailabilityMixin
from .const import DEVICE_TYPE_HOST

_LOGGER = logging.getLogger(__name__)
_EFFECTS = {
    "solid": "Solid",
    "breathe": "Breathe",
    "color_loop": "Color Loop",
}
_EFFECTS_REVERSE = {label: value for value, label in _EFFECTS.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    runtime = entry.runtime_data
    if runtime.device_type != DEVICE_TYPE_HOST or not runtime.device_id:
        return
    async_add_entities([VBotLEDLight(hass, runtime.device_id)])


class VBotLEDLight(MQTTAvailabilityMixin, LightEntity):
    """Represent the VBot LED output as an RGB light."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_color_mode = ColorMode.RGB
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, device: str) -> None:
        self._hass = hass
        self._device = device
        self._attr_name = "LED Effects Control"
        self._attr_unique_id = f"{device.lower()}_light_led"
        self._state_topic = f"{device}/light/led/state"
        self._command_topic = f"{device}/script/led_control/set"
        self._is_on = False
        self._rgb_color = (255, 180, 100)
        self._brightness = 255
        self._effect = "solid"
        self._effects = dict(_EFFECTS)
        self._supported = False
        self._pending_payload = {}
        self._pending_send_task = None

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        return self._rgb_color

    @property
    def brightness(self) -> int:
        return self._brightness

    @property
    def effect_list(self) -> list[str]:
        return list(self._effects.values())

    @property
    def effect(self) -> str:
        return self._effects.get(self._effect, self._effects.get("solid", "Solid"))

    @property
    def available(self) -> bool:
        return super().available and self._supported

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        unsubscribe = await mqtt.async_subscribe(
            self._hass, self._state_topic, self._message_received, qos=1
        )
        self.async_on_remove(unsubscribe)

    @callback
    def _message_received(self, message) -> None:
        try:
            data = json.loads(message.payload)
            color = data.get("rgb_color")
            if (
                not isinstance(data, dict)
                or type(data.get("on")) is not bool
                or not isinstance(color, list)
                or len(color) != 3
                or any(type(channel) is not int or not 0 <= channel <= 255 for channel in color)
            ):
                raise ValueError("invalid LED state")
            brightness = data.get("brightness")
            effect = str(data.get("effect") or "solid")
            effects = data.get("effects", _EFFECTS)
            if not isinstance(effects, dict) or not effects or any(not isinstance(key, str) or not isinstance(label, str) for key, label in effects.items()):
                raise ValueError("invalid VBot LED effect list")
            if type(brightness) is not int or not 0 <= brightness <= 255 or effect not in effects:
                raise ValueError("invalid LED brightness/effect")
            self._is_on = data["on"]
            self._rgb_color = tuple(color)
            self._brightness = brightness
            self._effect = effect
            self._effects = effects
            self._supported = data.get("supported") is True
            self.async_write_ha_state()
        except (TypeError, ValueError, AttributeError):
            _LOGGER.debug("Ignoring invalid VBot LED state for %s", self._device)

    async def async_turn_on(self, **kwargs) -> None:
        payload = {"action": "turn_on"}
        rgb_color = kwargs.get("rgb_color")
        if rgb_color is not None:
            if len(rgb_color) != 3:
                raise ValueError("rgb_color must have three channels")
            payload["rgb_color"] = [max(0, min(255, int(value))) for value in rgb_color]
        brightness = kwargs.get("brightness")
        if brightness is not None:
            payload["brightness"] = max(0, min(255, int(brightness)))
        effect = kwargs.get("effect")
        if effect is not None:
            reverse = {label: key for key, label in self._effects.items()}
            if effect not in reverse:
                raise ValueError("Unsupported VBot LED effect")
            payload["effect"] = reverse[effect]

        # Gộp cập nhật từ color picker/brightness slider; gửi trạng thái cuối
        # sau khi người dùng ngừng thao tác 0,5 giây.
        self._pending_payload.update(payload)
        if self._pending_send_task is not None:
            self._pending_send_task.cancel()
        self._pending_send_task = self._hass.async_create_task(
            self._async_send_after_quiet_period()
        )

    async def _async_send_after_quiet_period(self) -> None:
        try:
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            return
        payload = dict(self._pending_payload)
        self._pending_payload.clear()
        self._pending_send_task = None
        try:
            await mqtt.async_publish(
                self._hass, self._command_topic, json.dumps(payload), qos=1, retain=False
            )
        except Exception:
            _LOGGER.exception("Failed to publish LED control for %s", self._device)
    async def async_turn_off(self, **kwargs) -> None:
        if self._pending_send_task is not None:
            self._pending_send_task.cancel()
            self._pending_send_task = None
        self._pending_payload.clear()
        await mqtt.async_publish(
            self._hass,
            self._command_topic,
            json.dumps({"action": "turn_off"}),
            qos=1,
            retain=False,
        )
