from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException

from .models import StatusResponse
from .service import GitUpdateService


def create_app(service: GitUpdateService) -> FastAPI:
    app = FastAPI(title="Git Update", version="0.1.0")

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

    @app.get("/config")
    async def config() -> dict[str, Any]:
        return service.public_config()

    return app
