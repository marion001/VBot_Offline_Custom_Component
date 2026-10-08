"""Shared VBot update-checking and notification service."""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
import re

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .availability import is_vbot_device_online
from .api import VBotApiClient
from .const import DOMAIN, vbot_api_headers, vbot_host_from_url
from .update import UPDATE_DESCRIPTIONS, get_update_metadata_store

_LOGGER = logging.getLogger(__name__)


def _parse_release_date(value):
    text = str(value or "").strip()
    for date_format in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    return None


def _version_key(value):
    parts = re.findall(r"\d+", str(value or ""))
    return tuple(int(part) for part in parts) if parts else ()


def _is_remote_release_different(
    current_release_date,
    remote_release_date,
    current_version="",
    remote_version="",
):
    """Return whether release metadata differs, including intentional downgrade."""
    current_date = _parse_release_date(current_release_date)
    remote_date = _parse_release_date(remote_release_date)
    if current_date is not None and remote_date is not None:
        def normalized_version(value):
            value = str(value or '').strip()
            return value[1:] if len(value)>1 and value[0] in 'vV' and value[1].isdigit() else value
        current_key, remote_key = normalized_version(current_version), normalized_version(remote_version)
        return remote_date != current_date or bool(current_key and remote_key and current_key != remote_key)
    current_date_text = str(current_release_date or "").strip()
    remote_date_text = str(remote_release_date or "").strip()
    if current_date_text and remote_date_text and current_date_text != remote_date_text:
        return True
    current_key = _version_key(current_version)
    remote_key = _version_key(remote_version)
    return bool(current_key and remote_key and remote_key != current_key)


async def _async_get_local_release(hass, runtime, description):
    host = vbot_host_from_url(runtime.api_url)
    if not host:
        raise ValueError("VBot API URL does not contain a host")
    folder = "html/" if description.key == "interface" else ""
    url = (
        f"{runtime.client.webui_base_url}/includes/php_ajax/Show_file_path.php?read_file_path"
        f"&file=/home/pi/VBot_Offline/{folder}Version.json"
    )
    timeout = aiohttp.ClientTimeout(total=15, connect=10)
    async with async_get_clientsession(hass).get(
        url, headers=vbot_api_headers(runtime.api_key), timeout=timeout
    ) as response:
        response.raise_for_status()
        payload = await response.json(content_type=None)
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise ValueError("VBot local release response is invalid")
    release = payload.get("data")
    if isinstance(release, str):
        release = json.loads(release)
    if not isinstance(release, dict):
        raise ValueError("VBot local release metadata is invalid")
    return release


async def async_check_device_updates(hass, device_id, *, entry_id=None, notify_when_current=False):
    """Check both installable components through one shared implementation."""
    entry = next(
        (
            item
            for item in hass.config_entries.async_entries(DOMAIN)
            if (entry_id and item.entry_id == entry_id)
            or (not entry_id and getattr(getattr(item, "runtime_data", None), "device_id", None) == device_id)
        ),
        None,
    )
    if entry is None or getattr(entry, "runtime_data", None) is None or not is_vbot_device_online(hass, device_id):
        return []
    store = get_update_metadata_store(hass)
    # Button/switch checks are explicit user or timer requests and must not use
    # metadata left in the normal 12-hour entity polling cache.
    store.clear_cache()

    async def check(description):
        try:
            local, remote = await asyncio.gather(
                _async_get_local_release(hass, entry.runtime_data, description),
                store.async_get(description),
            )
            different = _is_remote_release_different(
                local.get("releaseDate") or local.get("release_date"),
                remote.get("releaseDate") or remote.get("release_date"),
                local.get("version"),
                remote.get("version"),
            )
            return {"description": description, "local": local, "remote": remote, "different": different}
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError, json.JSONDecodeError) as error:
            _LOGGER.warning("Không thể kiểm tra %s cho %s: %s", description.key, device_id, error)
            return None

    results = await asyncio.gather(*(check(item) for item in UPDATE_DESCRIPTIONS))
    valid_results = [item for item in results if item is not None]
    updates = [item for item in valid_results if item["different"]]
    await _async_notify_update_result(
        hass, device_id, entry.runtime_data.api_url, updates,
        checks_ok=len(valid_results) == len(UPDATE_DESCRIPTIONS),
        notify_when_current=notify_when_current,
    )
    from .update import async_refresh_vbot_updates
    await async_refresh_vbot_updates(hass, device_id)
    return updates


async def _async_notify_update_result(
    hass, device_id, api_url, updates, *, checks_ok, notify_when_current
):
    notification_id = f"vbot_updates_{device_id.casefold()}"
    if not updates and not notify_when_current:
        if checks_ok:
            await hass.services.async_call(
                "persistent_notification", "dismiss", {"notification_id": notification_id}
            )
        return
    if updates:
        lines = [f"Phát hiện {len(updates)} thành phần có metadata khác cho **{device_id}**:"]
        for item in updates:
            description = item["description"]
            remote = item["remote"]
            local = item.get('local', {})
            lines.append(
                f"- **{description.name}**: đang cài {local.get('version', 'N/A')} "
                f"({local.get('releaseDate', 'N/A')}); trên GitHub {remote.get('version', 'N/A')} "
                f"({remote.get('releaseDate', 'N/A')})"
            )
        host = vbot_host_from_url(api_url)
        if host:
            lines.append(f"\nKiểm tra thiết bị: {VBotApiClient(None, api_url).webui_base_url}")
        title = f"Có bản VBot khác ({device_id})"
        message = "\n".join(lines)
    elif checks_ok:
        title = f"VBot đang dùng metadata mới nhất ({device_id})"
        message = "Không phát hiện metadata chương trình hoặc WebUI khác."
    else:
        title = f"Không kiểm tra được cập nhật VBot ({device_id})"
        message = "Không đọc được đầy đủ metadata local hoặc metadata trên GitHub."
    await hass.services.async_call(
        "persistent_notification", "create",
        {"title": title, "message": message, "notification_id": notification_id},
    )
