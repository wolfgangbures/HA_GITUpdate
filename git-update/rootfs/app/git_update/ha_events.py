from __future__ import annotations

import logging
import os
from typing import Any

import httpx

_LOGGER = logging.getLogger(__name__)
SUPERVISOR_API = os.getenv("SUPERVISOR_API", "http://supervisor")
TOKEN = os.getenv("SUPERVISOR_TOKEN")
if not TOKEN:
    logging.getLogger(__name__).error(
        "SUPERVISOR_TOKEN missing. Enable homeassistant_api in config or restart the add-on after granting access."
    )


class HAEventClient:
    def __init__(self, event_name: str) -> None:
        self._event_name = event_name
        self._client = httpx.AsyncClient(timeout=20)

    async def fire_event(self, payload: dict[str, Any]) -> None:
        if not TOKEN:
            _LOGGER.warning("Supervisor token missing, skipping HA event emission")
            return
        url = f"{SUPERVISOR_API}/core/api/events/{self._event_name}"
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        }
        resp = await self._client.post(url, json=payload, headers=headers)
        resp.raise_for_status()

    async def aclose(self) -> None:
        await self._client.aclose()
