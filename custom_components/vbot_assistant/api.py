"""HTTP client for one VBot config entry."""

from __future__ import annotations

from typing import Any

import aiohttp

from .const import vbot_api_headers


class VBotApiClient:
    """Keep HTTP configuration isolated per VBot device."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_key: str = "") -> None:
        self._session = session
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key.strip()

    async def async_post(self, path: str, payload: dict[str, Any], *, timeout: float = 15) -> tuple[int, Any]:
        """Post JSON and return the HTTP status and decoded response."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Content-Type": "application/json", **vbot_api_headers(self._api_key)}
        request_timeout = aiohttp.ClientTimeout(total=timeout)
        async with self._session.post(url, json=payload, headers=headers, timeout=request_timeout) as response:
            if response.status == 200:
                return response.status, await response.json()
            return response.status, await response.text()
