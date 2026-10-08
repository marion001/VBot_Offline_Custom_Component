"""HTTP client for one VBot config entry."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import aiohttp

from .const import vbot_api_headers


class VBotApiClient:
    """Keep HTTP configuration isolated per VBot device."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_key: str = "") -> None:
        self._session = session
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key.strip()

    async def async_get_health(self, *, timeout: float = 5) -> bool:
        """Probe VBot once after reconnect. If no health endpoint exists, return False safely."""
        if not self.base_url:
            return False
        candidates = [
            f"{self.base_url}/health",
            f"{self.base_url}/api/status",
            f"{self.base_url}/api/health",
        ]
        headers = vbot_api_headers(self._api_key)
        request_timeout = aiohttp.ClientTimeout(total=timeout, connect=5)
        for url in candidates:
            try:
                async with self._session.get(url, headers=headers, timeout=request_timeout) as response:
                    if response.status == 200:
                        return True
                    if response.status in {404, 405}:
                        continue
                    return False
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                continue
        return False

    async def async_post(self, path: str, payload: dict[str, Any], *, timeout: float = 15) -> tuple[int, Any]:
        """Post JSON and return the HTTP status and decoded response."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Content-Type": "application/json", **vbot_api_headers(self._api_key)}
        request_timeout = aiohttp.ClientTimeout(total=timeout, connect=5)
        async with self._session.post(url, json=payload, headers=headers, timeout=request_timeout) as response:
            if response.status == 200:
                return response.status, await response.json()
            return response.status, await response.text()

    @property
    def webui_base_url(self) -> str:
        """Derive the WebUI origin from the conventional VBot API URL."""
        parsed = urlsplit(self.base_url)
        host = parsed.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        # The stock API listens on 5002 while the WebUI uses the default port.
        port = parsed.port
        netloc = host if port in (None, 5002) else parsed.netloc
        return urlunsplit((parsed.scheme or "http", netloc, "", "", "")).rstrip("/")

    async def async_webui_media_get(
        self,
        params: dict[str, str],
        *,
        timeout: float = 35,
    ) -> Any:
        """Call the existing WebUI media API with VBot API-key authentication."""
        url = f"{self.webui_base_url}/includes/php_ajax/Media_Player_Search.php"
        request_timeout = aiohttp.ClientTimeout(total=timeout, connect=5)
        async with self._session.get(
            url,
            params=params,
            headers=vbot_api_headers(self._api_key),
            timeout=request_timeout,
        ) as response:
            response.raise_for_status()
            return await response.json(content_type=None)
