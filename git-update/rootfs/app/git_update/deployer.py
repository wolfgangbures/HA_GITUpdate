from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Iterable

import yaml

from .config import Options, REPO_DIR
from .models import FileChange

_LOGGER = logging.getLogger(__name__)


class DeploymentError(RuntimeError):
    """Raised when deploying a change fails."""


class FileDeployer:
    def __init__(self, options: Options) -> None:
        self._repo_dir = REPO_DIR.resolve()
        self._target_base = Path(options.target_path).resolve()
        self._target_base.mkdir(parents=True, exist_ok=True)

    def deploy(self, changes: Iterable[FileChange]) -> None:
        for change in changes:
            self._apply_change(change)

    def _apply_change(self, change: FileChange) -> None:
        repo_path = (self._repo_dir / change.path).resolve()
        target_path = (self._target_base / change.path).resolve()

        self._guard_repo_path(repo_path)
        self._guard_path(target_path)

        if change.change_type in {"added", "modified"}:
            self._copy_file(repo_path, target_path)
        elif change.change_type == "renamed":
            if change.previous_path:
                old_target = (self._target_base / change.previous_path).resolve()
                if old_target.exists():
                    _LOGGER.debug("Removing renamed target %s", old_target)
                    try:
                        old_target.unlink()
                    except OSError as exc:
                        raise DeploymentError(f"Failed to remove {old_target}: {exc}") from exc
            self._copy_file(repo_path, target_path)
        elif change.change_type == "deleted":
            if target_path.exists():
                _LOGGER.info("Removing deleted file %s", target_path)
                try:
                    target_path.unlink()
                except OSError as exc:
                    raise DeploymentError(f"Failed to remove {target_path}: {exc}") from exc
        else:
            _LOGGER.warning("Unknown change type %s for %s", change.change_type, change.path)

    def _copy_file(self, repo_path: Path, target_path: Path) -> None:
        if not repo_path.exists():
            _LOGGER.warning("Repository file %s missing, skipping", repo_path)
            return
        if repo_path.suffix in {".yaml", ".yml"}:
            self._validate_yaml(repo_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        _LOGGER.info("Deploying %s -> %s", repo_path, target_path)
        try:
            shutil.copy2(repo_path, target_path)
        except OSError as exc:
            raise DeploymentError(f"Failed to copy {repo_path} to {target_path}: {exc}") from exc

    def _validate_yaml(self, path: Path) -> None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise DeploymentError(f"Invalid YAML in {path}: {exc}") from exc

    def _guard_path(self, path: Path) -> None:
        try:
            path.relative_to(self._target_base)
        except ValueError as exc:
            raise DeploymentError(f"Unsafe target path {path}") from exc

    def _guard_repo_path(self, path: Path) -> None:
        try:
            path.relative_to(self._repo_dir)
        except ValueError as exc:
            raise DeploymentError(f"Unsafe repository path {path}") from exc
*** End Patch