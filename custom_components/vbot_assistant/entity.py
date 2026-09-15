"""Shared entity helpers for VBot Assistant."""

from .const import DOMAIN


class VBotEntity:
    """Provide the common Home Assistant device association."""

    _device: str | None = None

    @property
    def device_info(self):
        if not self._device:
            return None
        return {
            "identifiers": {(DOMAIN, self._device)},
            "name": f"{self._device} VBot Assistant",
            "manufacturer": "Vũ Tuyển",
            "model": "VBot Assistant MQTT",
        }
