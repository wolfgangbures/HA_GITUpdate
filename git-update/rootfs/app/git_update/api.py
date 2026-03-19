from __future__ import annotations

import json
import os
from typing import Any

from fastapi import FastAPI

from .models import StatusResponse
from .service import GitUpdateService


def _get_version() -> str:
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.json")
    try:
        with open(os.path.normpath(config_path)) as f:
            return json.load(f).get("version", "unknown")
    except Exception:
        return "unknown"


def create_app(service: GitUpdateService) -> FastAPI:
    app = FastAPI(title="Git Update", version=_get_version())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/status", response_model=StatusResponse)
    async def status() -> StatusResponse:
        return service.status

    @app.post("/sync")
    async def manual_sync(body: dict[str, Any] | None = None) -> StatusResponse:
        reason = (body or {}).get("reason", "manual")
        await service.trigger_sync(reason)
        return service.status

    @app.post("/full-sync")
    async def full_sync(body: dict[str, Any] | None = None) -> StatusResponse:
        reason = (body or {}).get("reason", "manual-full-sync")
        await service.trigger_full_sync(reason)
        return service.status

    @app.get("/config")
    async def config() -> dict[str, Any]:
        return service.public_config()

    return app
