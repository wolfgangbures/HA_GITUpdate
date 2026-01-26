from __future__ import annotations

import logging
import os
import json
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

    async def check_config(self) -> tuple[bool | None, str | None]:
        """Run `check_config` and wait for the outcome.

        Returns a tuple of (is_valid, error_details). `is_valid` becomes `None`
        when validation was skipped (e.g. no token available).
        """

        if self._supervisor_token:
            try:
                return await self._check_config_via_supervisor()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response else None
                if status == 403:
                    _LOGGER.error(
                        "Supervisor denied /core/check (403). Ensure this add-on was rebuilt with supervisor_api access and restarted so Supervisor can inject a fresh SUPERVISOR_TOKEN automatically. Falling back to ha_access_token when available."
                    )
                    if self._fallback_token:
                        return await self._check_config_via_service()
                    return None, "supervisor_forbidden"
                if status == 401:
                    _LOGGER.error(
                        "Supervisor token rejected (401). Refresh the injected SUPERVISOR_TOKEN to continue validating configs."
                    )
                    return None, "supervisor_unauthorized"
                raise
        if self._fallback_token:
            try:
                return await self._check_config_via_service()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response else None
                if status in {401, 403}:
                    _LOGGER.error(
                        "Home Assistant API token rejected (%s). Update the ha_access_token (long-lived user token) in the add-on options.",
                        status,
                    )
                    return None, f"ha_api_{status}"
                raise

        _LOGGER.warning("HA token unavailable, skipping config check")
        return None, "missing_token"

    async def _check_config_via_supervisor(self) -> tuple[bool, str | None]:
        url = f"{SUPERVISOR_API}/core/check"
        headers = {
            "Authorization": f"Bearer {self._supervisor_token}",
            "Content-Type": "application/json",
        }

        resp = await self._client.post(url, json={}, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data", payload)
        result = data.get("result")
        errors = self._stringify_errors(data.get("errors"))

        if result == "valid":
            return True, None
        if result == "invalid":
            return False, errors or "Unknown configuration error"

        _LOGGER.warning("Unexpected response from /core/check: %s", data)
        return False, errors or json.dumps(data)

    async def _check_config_via_service(self) -> tuple[bool | None, str | None]:
        # Fallback for non-supervisor environments where only the standard
        # service call is available. The Home Assistant API responds once the
        # check is complete, but some installations return a simple list.
        url = f"{self._base_url}/api/services/homeassistant/check_config"
        headers = {
            "Authorization": f"Bearer {self._fallback_token}",
            "Content-Type": "application/json",
        }

        resp = await self._client.post(url, json={}, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list):
            # Empty list == valid
            return (not data), self._stringify_errors(data) if data else None

        if isinstance(data, dict):
            result = data.get("result")
            errors = self._stringify_errors(data.get("errors") or data.get("message"))
            if result == "valid":
                return True, None
            if result == "invalid":
                return False, errors or "Unknown configuration error"
            if errors:
                return False, errors
            return True, None

        _LOGGER.warning("Unknown payload from check_config service: %s", data)
        return None, self._stringify_errors(data)

    @staticmethod
    def _stringify_errors(value: Any) -> str | None:
        if value in (None, ""):
            return None
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except TypeError:
            return str(value)

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
