from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .config import Options

_LOGGER = logging.getLogger(__name__)
SUPERVISOR_API = os.getenv("SUPERVISOR_API", "http://supervisor")
SUPERVISOR_TOKEN_ENV = os.getenv("SUPERVISOR_TOKEN")


class HAEventClient:
    def __init__(self, options: Options) -> None:
        self._event_name = options.ha_event_name
        self._supervisor_token = SUPERVISOR_TOKEN_ENV
        self._fallback_token = options.ha_access_token or None
        self._base_url = (options.ha_base_url or "http://homeassistant:8123").rstrip("/")
        self._verify_ssl = options.ha_verify_ssl

        if self._supervisor_token:
            _LOGGER.debug("Using Supervisor token for HA events")
        elif self._fallback_token:
            _LOGGER.info("Using configured HA token for event emission via %s", self._base_url)
        else:
            _LOGGER.warning(
                "No Supervisor or configured HA token available; event emission disabled."
            )

        self._client = httpx.AsyncClient(timeout=20, verify=self._verify_ssl)

    async def check_config(self) -> Any:
        """Check Home Assistant configuration validity.
        
        Returns the service call response (typically a list).
        Empty list = valid config, non-empty = errors.
        """
        token: str | None
        url: str

        if self._supervisor_token:
            token = self._supervisor_token
            url = f"{SUPERVISOR_API}/core/api/services/homeassistant/check_config"
        elif self._fallback_token:
            token = self._fallback_token
            url = f"{self._base_url}/api/services/homeassistant/check_config"
        else:
            _LOGGER.warning("HA token unavailable, skipping config check")
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        resp = await self._client.post(url, json={}, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def fire_event(self, payload: dict[str, Any]) -> None:
        token: str | None
        url: str

        if self._supervisor_token:
            token = self._supervisor_token
            url = f"{SUPERVISOR_API}/core/api/events/{self._event_name}"
        elif self._fallback_token:
            token = self._fallback_token
            url = f"{self._base_url}/api/events/{self._event_name}"
        else:
            _LOGGER.warning("HA token unavailable, skipping event emission")
            return

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        resp = await self._client.post(url, json=payload, headers=headers)
        resp.raise_for_status()

    async def aclose(self) -> None:
        await self._client.aclose()
