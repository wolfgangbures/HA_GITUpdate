from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import git

from .config import Options, REPO_DIR
from .models import FileChange

_LOGGER = logging.getLogger(__name__)


@dataclass
class GitSyncResult:
    before: str | None
    after: str | None
    branch: str
    changes: list[FileChange]


class GitRepoManager:
    def __init__(self, options: Options, repo_dir: Path = REPO_DIR) -> None:
        self._options = options
        self._repo_dir = repo_dir
        self._repo: git.Repo | None = None
        if not self._options.verify_ssl:
            git.Git().update_environment(GIT_SSL_NO_VERIFY="true")

    def ensure_repo(self) -> git.Repo:
        if self._repo is not None:
            return self._repo
        if self._repo_dir.exists():
            self._repo = git.Repo(self._repo_dir)
        else:
            self._repo_dir.mkdir(parents=True, exist_ok=True)
            _LOGGER.info("Cloning %s", self._options.repo_url)
            clone_kwargs: dict[str, object] = {"branch": self._options.branch}
            if self._depth_arg:
                clone_kwargs["depth"] = self._depth_arg
            self._repo = git.Repo.clone_from(
                self._auth_repo_url,
                self._repo_dir,
                **clone_kwargs,
            )
        return self._repo

    @property
    def _depth_arg(self) -> int | None:
        return None if self._options.git_depth == 0 else self._options.git_depth

    @property
    def _auth_repo_url(self) -> str:
        token = self._options.access_token or os.getenv("GIT_ACCESS_TOKEN")
        if token and self._options.repo_url.startswith("https://"):
            parts = self._options.repo_url.split("https://", maxsplit=1)[1]
            return f"https://{token}@{parts}"
        return self._options.repo_url

    def sync(self) -> GitSyncResult:
        repo = self.ensure_repo()
        before = self._safe_head(repo)
        branch = self._options.branch
        origin = repo.remotes.origin
        fetch_kwargs = {}
        if self._depth_arg:
            fetch_kwargs["depth"] = self._depth_arg
        origin.fetch(branch, **fetch_kwargs)
        repo.git.checkout(branch)
        origin.pull(branch)
        after = self._safe_head(repo)
        changes = self._collect_changes(repo, before, after)
        return GitSyncResult(before, after, branch, changes)

    def _collect_changes(
        self, repo: git.Repo, before: str | None, after: str | None
    ) -> list[FileChange]:
        if not before or not after or before == after:
            return []
        diff_output = repo.git.diff("--name-status", f"{before}..{after}")
        changes: list[FileChange] = []
        for line in diff_output.splitlines():
            if not line.strip():
                continue
            status, path, *rest = line.split("\t")
            if status.startswith("R"):
                new_path = rest[0] if rest else path
                changes.append(
                    FileChange(path=new_path, change_type="renamed", previous_path=path)
                )
                continue
            change_type = self._map_status(status)
            changes.append(FileChange(path=path, change_type=change_type))
        return changes

    @staticmethod
    def _map_status(status: str) -> str:
        mapping = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
        }
        return mapping.get(status, "modified")

    @staticmethod
    def _safe_head(repo: git.Repo) -> str | None:
        try:
            return repo.head.commit.hexsha
        except ValueError:
            return None
