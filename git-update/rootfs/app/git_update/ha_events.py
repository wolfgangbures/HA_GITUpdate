from __future__ import annotations

import logging
import os
from typing import Any

import httpx

_LOGGER = logging.getLogger(__name__)
SUPERVISOR_API = os.getenv("SUPERVISOR_API", "http://supervisor")
SUPERVISOR_TOKEN_ENV = os.getenv("SUPERVISOR_TOKEN")


class HAEventClient:
    def __init__(self, event_name: str, fallback_token: str | None = None) -> None:
        self._event_name = event_name
        self._token = SUPERVISOR_TOKEN_ENV or fallback_token
        if not self._token:
            logging.getLogger(__name__).warning(
                "No Supervisor or configured HA token available; event emission disabled."
            )
        elif fallback_token and not SUPERVISOR_TOKEN_ENV:
            logging.getLogger(__name__).info(
                "Using configured Home Assistant token for event emission."
            )
        self._client = httpx.AsyncClient(timeout=20)

    async def fire_event(self, payload: dict[str, Any]) -> None:
        if not self._token:
            _LOGGER.warning("HA token unavailable, skipping event emission")
            return
        url = f"{SUPERVISOR_API}/core/api/events/{self._event_name}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        resp = await self._client.post(url, json=payload, headers=headers)
        resp.raise_for_status()

    async def aclose(self) -> None:
        await self._client.aclose()
