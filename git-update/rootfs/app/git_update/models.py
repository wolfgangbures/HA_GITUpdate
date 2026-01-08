from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FileChange(BaseModel):
    path: str
    change_type: Literal["added", "modified", "deleted", "renamed"]
    previous_path: str | None = None


class SyncMetadata(BaseModel):
    commit_before: str | None = None
    commit_after: str | None = None
    branch: str
    changes: list[FileChange] = Field(default_factory=list)
    synced_at: datetime
    reason: str
    initial_sync: bool = False


class StatusResponse(BaseModel):
    healthy: bool
    last_sync: SyncMetadata | None = None
    pending_reason: str | None = None
    error: str | None = None
