"""Browsable and searchable VBot media source backed by the existing WebUI API."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Any

import aiohttp
from homeassistant.components.media_player import (
    BrowseError,
    MediaClass,
    MediaType,
    SearchMedia,
    SearchMediaQuery,
)
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant

from .const import DEVICE_TYPE_HOST, DOMAIN

_LOGGER = logging.getLogger(__name__)

_SOURCES = {
    "local": ("Nhạc Local", "Local"),
    "playlists": ("Playlist", None),
    "radio": ("Radio", "Radio"),
    "zing": ("Zing MP3", "ZingMP3_Search"),
    "youtube": ("YouTube", "Youtube_Search"),
    "nhaccuatui": ("NhacCuaTui", "NhacCuaTui_Search"),
    "podcast": ("Podcast", "podcast_Search"),
}
_SEARCHABLE = {"zing", "youtube", "nhaccuatui", "podcast"}
_CACHE_PARAMETERS = {
    "zing": "Cache_ZingMP3",
    "youtube": "Cache_Youtube",
    "nhaccuatui": "Cache_NhacCuaTui",
    "podcast": "Cache_PodCast",
}


def _encode_item(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_item(value: str) -> dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        payload = json.loads(raw.decode())
    except (ValueError, UnicodeError, json.JSONDecodeError) as error:
        raise Unresolvable("Dữ liệu media VBot không hợp lệ") from error
    if not isinstance(payload, dict):
        raise Unresolvable("Dữ liệu media VBot không hợp lệ")
    return payload


def media_source_metadata(media_id: str) -> dict[str, Any]:
    """Recover display metadata embedded in one VBot media-source URI."""
    prefix = f"media-source://{DOMAIN}/item/"
    if not media_id.startswith(prefix):
        return {}
    try:
        return _decode_item(media_id[len(prefix):])
    except Unresolvable:
        return {}


async def async_get_media_source(hass: HomeAssistant) -> "VBotMediaSource":
    """Return the global VBot media source."""
    return VBotMediaSource(hass)


class VBotMediaSource(MediaSource):
    """Expose media libraries from all configured VBot hosts."""

    name = "VBot"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    def _runtime(self, entry_id: str):
        entry = self.hass.config_entries.async_get_entry(entry_id)
        runtime = getattr(entry, "runtime_data", None) if entry else None
        if runtime is None or runtime.device_type != DEVICE_TYPE_HOST:
            raise BrowseError("Thiết bị VBot không sẵn sàng")
        return runtime

    @staticmethod
    def _error_text(value: Any) -> str:
        """Turn nested provider errors into text the HA frontend can render."""
        if isinstance(value, dict):
            for key in ("message", "error_description", "error", "status"):
                if value.get(key):
                    return VBotMediaSource._error_text(value[key])
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if isinstance(value, list):
            return "; ".join(VBotMediaSource._error_text(item) for item in value)
        return str(value or "Lỗi không xác định")

    @staticmethod
    def _rows(payload: Any) -> list[dict[str, Any]]:
        """Validate a WebUI response instead of hiding API/login failures."""
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if not isinstance(payload, dict):
            raise ValueError("WebUI trả về dữ liệu media không hợp lệ")
        if payload.get("success") is False or payload.get("error"):
            message = payload.get("message") or payload.get("error")
            raise ValueError(VBotMediaSource._error_text(message or "WebUI không thể tải dữ liệu media"))
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            raise ValueError("Danh sách media WebUI không hợp lệ")
        return [row for row in rows if isinstance(row, dict)]

    @staticmethod
    def _playlist_manifest_rows(payload: Any) -> list[dict[str, Any]]:
        """Validate playlist-manager responses, including WebUI login errors."""
        if not isinstance(payload, dict):
            raise ValueError("WebUI trả về danh sách playlist không hợp lệ")
        if payload.get("success") is False:
            raise ValueError(VBotMediaSource._error_text(
                payload.get("message") or "Không thể tải danh sách playlist"
            ))
        playlists = payload.get("playlists")
        if not isinstance(playlists, list):
            raise ValueError(
                "PHP Media_Player_Search.php chưa hỗ trợ Media Source hoặc chưa được cập nhật"
            )
        return [row for row in playlists if isinstance(row, dict)]

    @staticmethod
    def _node(
        identifier: str | None,
        title: str,
        *,
        playable: bool = False,
        expandable: bool = False,
        searchable: bool = False,
        thumbnail: str | None = None,
        media_class: MediaClass = MediaClass.DIRECTORY,
    ) -> BrowseMediaSource:
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=identifier,
            media_class=media_class,
            media_content_type=MediaType.MUSIC,
            title=title,
            can_play=playable,
            can_expand=expandable,
            can_search=searchable,
            thumbnail=thumbnail,
        )

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse devices, sources, playlists, and cached media."""
        parts = (item.identifier or "").split("/", 2)
        if not item.identifier:
            children = []
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                runtime = getattr(entry, "runtime_data", None)
                if runtime is not None and runtime.device_type == DEVICE_TYPE_HOST:
                    children.append(self._node(entry.entry_id, runtime.device_id, expandable=True))
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=None,
                media_class=MediaClass.APP,
                media_content_type=MediaType.MUSIC,
                title="VBot",
                can_play=False,
                can_expand=True,
                children=children,
            )

        entry_id = parts[0]
        runtime = self._runtime(entry_id)
        if len(parts) == 1:
            children = [
                self._node(
                    f"{entry_id}/{key}",
                    label,
                    expandable=True,
                    searchable=key in _SEARCHABLE,
                )
                for key, (label, _parameter) in _SOURCES.items()
            ]
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=entry_id,
                media_class=MediaClass.APP,
                media_content_type=MediaType.MUSIC,
                title=runtime.device_id,
                can_play=False,
                can_expand=True,
                can_search=True,
                search_media_classes=[MediaClass.MUSIC, MediaClass.TRACK, MediaClass.PODCAST],
                children=children,
            )

        source = parts[1]
        if source in _SEARCHABLE:
            try:
                payload = await runtime.client.async_webui_media_get(
                    {_CACHE_PARAMETERS[source]: "1"}
                )
                rows = self._rows(payload)
                children = self._tracks(entry_id, rows, source)
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError) as error:
                _LOGGER.warning(
                    "Không thể tải cache %s cho %s: %s",
                    _SOURCES[source][0],
                    runtime.device_id,
                    error,
                )
                children = []
            return self._folder(
                item.identifier,
                _SOURCES[source][0],
                children,
                searchable=True,
            )
        try:
            if source == "playlists":
                if len(parts) == 2:
                    payload = await runtime.client.async_webui_media_get({"Playlist_Manager": "1"})
                    playlists = self._playlist_manifest_rows(payload)
                    children = [
                        self._node(
                            f"{entry_id}/playlists/{row.get('id')}",
                            str(row.get("name") or row.get("id") or "Playlist"),
                            expandable=True,
                        )
                        for row in playlists
                        if row.get("id")
                    ]
                    return self._folder(item.identifier, "Playlist", children)
                payload = await runtime.client.async_webui_media_get(
                    {"Cache_PlayList": "1", "playlist_id": parts[2]}
                )
                rows = self._rows(payload)
                playlist_name = str(payload.get("playlist_name") or "Playlist")
                play_all = {
                    "entry_id": entry_id,
                    "action": "playlist",
                    "playlist_id": parts[2],
                    "title": playlist_name,
                    "source": "playlist",
                    "source_label": "Playlist",
                }
                children = [
                    self._node(
                        f"item/{_encode_item(play_all)}",
                        f"▶ Phát toàn bộ — {playlist_name}",
                        playable=True,
                        media_class=MediaClass.PLAYLIST,
                    ),
                    *self._tracks(entry_id, rows),
                ]
                return self._folder(item.identifier, playlist_name, children)

            parameter = _SOURCES.get(source, (None, None))[1]
            if parameter is None:
                raise BrowseError("Nguồn media VBot không hợp lệ")
            payload = await runtime.client.async_webui_media_get({parameter: "1"})
            rows = self._rows(payload)
            return self._folder(item.identifier, _SOURCES[source][0], self._tracks(entry_id, rows, source))
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError) as error:
            raise BrowseError(f"Không thể tải media từ {runtime.device_id}: {error}") from error

    def _folder(
        self,
        identifier: str,
        title: str,
        children: list[BrowseMediaSource],
        *,
        searchable: bool = False,
    ) -> BrowseMediaSource:
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=identifier,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title=title,
            can_play=False,
            can_expand=True,
            can_search=searchable,
            search_media_classes=[MediaClass.MUSIC, MediaClass.TRACK, MediaClass.PODCAST]
            if searchable else None,
            children=children,
        )

    def _tracks(self, entry_id: str, rows: Any, source: str | None = None) -> list[BrowseMediaSource]:
        result = []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            normalized = self._normalize_row(entry_id, row, source)
            if not normalized.get("url") and not normalized.get("id"):
                continue
            result.append(self._node(
                f"item/{_encode_item(normalized)}",
                normalized["title"],
                playable=True,
                thumbnail=normalized.get("thumbnail"),
                media_class=MediaClass.PODCAST if normalized.get("source") == "podcast" else MediaClass.MUSIC,
            ))
        return result

    @staticmethod
    def _normalize_row(entry_id: str, row: dict[str, Any], source: str | None) -> dict[str, Any]:
        detected = (source or str(row.get("source") or "")).lower()
        aliases = {"zingmp3": "zing", "youtube": "youtube", "nhaccuatui": "nhaccuatui"}
        detected = aliases.get(detected, detected)
        source_label = {
            "zing": "Zing MP3",
            "youtube": "YouTube",
            "nhaccuatui": "NhacCuaTui",
            "podcast": "Podcast",
            "local": "Nhạc Local",
            "radio": "Radio",
        }.get(detected, str(row.get("source") or "VBot"))
        title = str(row.get("title") or row.get("name") or "Không rõ tên")
        artist = str(row.get("artist") or row.get("channelTitle") or "").strip()
        if artist:
            title = f"{title} — {artist}"
        return {
            "entry_id": entry_id,
            "source": detected,
            "source_label": source_label,
            "id": row.get("id") or row.get("audio"),
            "url": row.get("url") or row.get("link") or row.get("audio") or row.get("full_path"),
            "title": title,
            "thumbnail": row.get("thumb") or row.get("cover"),
        }

    async def async_search_media(self, item: MediaSourceItem, query: SearchMediaQuery) -> SearchMedia:
        """Search one source or all WebUI online providers for a VBot."""
        parts = (item.identifier or "").split("/")
        if not parts or not parts[0]:
            raise BrowseError("Hãy chọn một thiết bị VBot trước khi tìm kiếm")
        entry_id = parts[0]
        runtime = self._runtime(entry_id)
        sources = [parts[1]] if len(parts) > 1 and parts[1] in _SEARCHABLE else sorted(_SEARCHABLE)

        async def search(source: str) -> tuple[list[BrowseMediaSource], str | None]:
            text = query.search_query.strip()
            params = {
                "zing": {"ZingMP3_Search": "1", "SongName": text},
                "youtube": {"Youtube_Search": "1", "Name": text, "Limit": "20"},
                "nhaccuatui": {"NhacCuaTui_Search": "1", "SongName": text},
                "podcast": {"podcast_Search": "1", "PodCastName": text, "Limit": "20"},
            }[source]
            try:
                payload = await runtime.client.async_webui_media_get(params)
                rows = self._rows(payload)
                return self._tracks(entry_id, rows, source), None
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError) as error:
                return [], f"{_SOURCES[source][0]}: {error}"

        groups = await asyncio.gather(*(search(source) for source in sources))
        tracks = [track for group, _error in groups for track in group]
        if query.media_filter_classes:
            allowed_classes = set(query.media_filter_classes)
            tracks = [
                track for track in tracks
                if track.media_class in allowed_classes
            ]
        errors = [error for _group, error in groups if error]
        if not tracks and errors:
            message = "; ".join(errors)
            _LOGGER.warning("Tìm kiếm media VBot thất bại cho %s: %s", runtime.device_id, message)
            # HA frontend can render provider errors returned as browse items;
            # websocket BrowseError objects may otherwise appear as [object Object].
            tracks.append(self._node(
                f"{entry_id}/search-error",
                f"Lỗi tìm kiếm: {message}",
                media_class=MediaClass.DIRECTORY,
            ))
        return SearchMedia(result=tracks)

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a selected WebUI result into a URL/path VBot can play."""
        identifier = item.identifier or ""
        if not identifier.startswith("item/"):
            raise Unresolvable("Mục VBot này không thể phát trực tiếp")
        payload = _decode_item(identifier[5:])
        if payload.get("action") == "playlist":
            raise Unresolvable("Playlist VBot chỉ có thể phát trên Media Player VBot")
        runtime = self._runtime(str(payload.get("entry_id") or ""))
        source = str(payload.get("source") or "").lower()
        url = str(payload.get("url") or "").strip()
        media_id = str(payload.get("id") or "").strip()
        try:
            if source == "zing" and media_id:
                resolved = await runtime.client.async_webui_media_get(
                    {"ZingMP3_GetLink": "1", "Zing_ID": media_id}
                )
                url = str(resolved.get("url") or "")
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError) as error:
            raise Unresolvable(f"Không thể lấy link phát VBot: {error}") from error
        if not url:
            raise Unresolvable("Nguồn không trả về link phát")
        if source == "local" and url.startswith("/"):
            # This path belongs to the VBot host, not Home Assistant. Preserve
            # it explicitly so the VBot player does not turn it into a HA URL.
            return PlayMedia(url, "audio/mpeg", path=Path(url))
        return PlayMedia(url, "audio/mpeg")
