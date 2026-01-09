from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from .config import Options, load_options
from .deployer import DeploymentError, FileDeployer
from .git_client import GitRepoManager
from .models import StatusResponse, SyncMetadata
from .notifier import Notifier

_LOGGER = logging.getLogger(__name__)


class GitUpdateService:
    def __init__(self, options: Options | None = None) -> None:
        self.options = options or load_options()
        self.repo = GitRepoManager(self.options)
        self.deployer = FileDeployer(self.options)
        self.notifier = Notifier(self.options)
        self.status = StatusResponse(healthy=True, last_sync=None, pending_reason=None, error=None)
        self._sync_lock = asyncio.Lock()
        self._stop = asyncio.Event()

    async def run(self) -> None:
        if self.options.notify_on_startup:
            await self.trigger_sync("startup")
        while not self._stop.is_set():
            await self.trigger_sync("scheduled")
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.options.poll_interval
                )
            except asyncio.TimeoutError:
                continue

    async def trigger_sync(self, reason: str) -> None:
        async with self._sync_lock:
            await self._execute_sync(reason)

    async def _execute_sync(self, reason: str) -> None:
        self.status = StatusResponse(
            healthy=self.status.healthy,
            last_sync=self.status.last_sync,
            pending_reason=reason,
            error=self.status.error,
        )
        try:
            result = await asyncio.to_thread(self.repo.sync)
            metadata = SyncMetadata(
                commit_before=result.before,
                commit_after=result.after,
                branch=result.branch,
                changes=result.changes,
                synced_at=datetime.now(timezone.utc),
                reason=reason,
                initial_sync=result.initial,
            )
            if result.changes:
                try:
                    await asyncio.to_thread(self.deployer.deploy, result.changes)
                except DeploymentError as exc:
                    _LOGGER.error("Deployment failed: %s", exc)
                    await self.notifier.notify_error(
                        "deployment_error",
                        str(exc),
                        result.branch,
                        result.after,
                    )
                    self.status = StatusResponse(
                        healthy=False,
                        last_sync=metadata,
                        pending_reason=None,
                        error=str(exc),
                    )
                    return

                # Validate Home Assistant configuration
                check_result = await self.notifier._ha.check_config()
                if check_result is not None and check_result:
                    # Non-empty response means validation errors
                    error_msg = f"Home Assistant configuration invalid: {check_result}"
                    _LOGGER.error(error_msg)
                    await self.notifier.notify_error(
                        "config_validation_error",
                        error_msg,
                        result.branch,
                        result.after,
                    )
                    self.status = StatusResponse(
                        healthy=False,
                        last_sync=metadata,
                        pending_reason=None,
                        error=error_msg,
                    )
                    return

            self.status = StatusResponse(healthy=True, last_sync=metadata, pending_reason=None, error=None)
            
            if result.changes:
                _LOGGER.info("Sync completed: %d file(s) changed on branch %s @ %s", 
                            len(result.changes), result.branch, result.after[:7] if result.after else "unknown")
            else:
                _LOGGER.debug("Sync completed: no changes detected on branch %s @ %s",
                             result.branch, result.after[:7] if result.after else "unknown")
            
            should_notify = bool(result.changes) or (
                self.options.notify_on_startup and reason == "startup"
            )
            if should_notify:
                await self.notifier.notify(result.changes, result.branch, result.after, reason)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("Sync failed: %s", exc)
            self.status = StatusResponse(
                healthy=False,
                last_sync=self.status.last_sync,
                pending_reason=None,
                error=str(exc),
            )

    def public_config(self) -> dict[str, Any]:
        data = self.options.model_dump()
        data.pop("access_token", None)
        data.pop("ha_access_token", None)
        if data.get("ha_base_url"):
            data["ha_base_url"] = "***redacted***"
        data.pop("mqtt_password", None)
        return data

    async def shutdown(self) -> None:
        self._stop.set()
        await self.notifier.aclose()
