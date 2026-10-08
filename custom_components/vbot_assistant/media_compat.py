"""Compatibility checks for the VBot WebUI media API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .repairs import update_api_auth_issue, update_media_api_issue

_LOGGER = logging.getLogger(__name__)
MIN_MEDIA_API_VERSION = 2
REQUIRED_MEDIA_CAPABILITIES = frozenset({
    "local",
    "playlist",
    "playlist_play_all",
    "radio",
    "search",
    "cache",
    "youtube_direct",
})
_STORE = "media_api_compatibility"


def get_media_api_compatibility(hass: HomeAssistant, device_id: str) -> dict[str, Any] | None:
    """Return the latest non-sensitive compatibility result."""
    result = hass.data.get(DOMAIN, {}).get(_STORE, {}).get(device_id)
    return dict(result) if isinstance(result, dict) else None


async def async_check_media_api_compatibility(
    hass: HomeAssistant,
    runtime: Any,
) -> bool | None:
    """Check one host without treating temporary connectivity as old software."""
    try:
        payload = await runtime.client.async_webui_media_get(
            {"Media_Source_Health": "1"},
            timeout=8,
        )
    except aiohttp.ClientResponseError as error:
        if error.status == 401:
            update_api_auth_issue(
                hass, runtime.device_id, authentication_failed=True
            )
            entry = hass.config_entries.async_get_entry(runtime.entry_id)
            if entry is not None:
                entry.async_start_reauth_if_available(hass)
        _LOGGER.debug(
            "Không thể kiểm tra Media API cho %s: %s", runtime.device_id, error
        )
        return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        _LOGGER.debug(
            "Tạm hoãn kiểm tra Media API cho %s vì không kết nối được: %s",
            runtime.device_id,
            error,
        )
        return None
    except (ValueError, TypeError) as error:
        payload = {"success": False, "message": str(error)}

    version = 0
    update_api_auth_issue(hass, runtime.device_id, authentication_failed=False)
    capabilities: set[str] = set()
    if isinstance(payload, dict):
        try:
            version = int(payload.get("media_api_version") or 0)
        except (TypeError, ValueError):
            version = 0
        raw_capabilities = payload.get("capabilities")
        if isinstance(raw_capabilities, list):
            capabilities = {
                str(capability).strip()
                for capability in raw_capabilities
                if str(capability).strip()
            }

    missing = sorted(REQUIRED_MEDIA_CAPABILITIES - capabilities)
    compatible = version >= MIN_MEDIA_API_VERSION and not missing
    store = hass.data.setdefault(DOMAIN, {}).setdefault(_STORE, {})
    store[runtime.device_id] = {
        "compatible": compatible,
        "version": version or None,
        "minimum_version": MIN_MEDIA_API_VERSION,
        "missing_capabilities": missing,
    }
    runtime.set_capabilities("media", capabilities, scope=REQUIRED_MEDIA_CAPABILITIES)
    runtime.media_api_version = version or None
    update_media_api_issue(
        hass,
        runtime.device_id,
        compatible=compatible,
        current_version=version or None,
        minimum_version=MIN_MEDIA_API_VERSION,
        missing_capabilities=missing,
    )

    if compatible:
        return True

    detail = "Không nhận được thông tin phiên bản Media API."
    if version:
        detail = f"Media API hiện tại: {version}; yêu cầu tối thiểu: {MIN_MEDIA_API_VERSION}."
    if missing:
        detail += " Thiếu khả năng: " + ", ".join(missing) + "."
    if isinstance(payload, dict) and payload.get("message"):
        detail += f" Phản hồi WebUI: {payload['message']}"
    _LOGGER.warning(
        "%s cần cập nhật Media API: %s Hãy cập nhật Media_Player_Search.php "
        "trên thiết bị và khởi động lại Apache. Nếu API Auth đang bật, hãy "
        "kiểm tra lại VBot-API-Key trong Reconfigure.",
        runtime.device_id,
        detail,
    )
    return False
