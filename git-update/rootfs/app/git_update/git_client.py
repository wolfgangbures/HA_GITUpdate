from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import git

from .config import Options, REPO_DIR
from .models import FileChange
from .secrets import redact_url

_LOGGER = logging.getLogger(__name__)


@dataclass
class GitSyncResult:
    before: str | None
    after: str | None
    branch: str
    changes: list[FileChange]
    initial: bool = False


class GitRepoManager:
    def __init__(self, options: Options, repo_dir: Path = REPO_DIR) -> None:
        self._options = options
        self._repo_dir = repo_dir
        self._repo: git.Repo | None = None
        self._askpass_preflight_done = False
        if not self._options.verify_ssl:
            git.Git().update_environment(GIT_SSL_NO_VERIFY="true")

    def preflight(self) -> None:
        """Run lightweight startup checks for Git authentication helpers."""
        self._preflight_askpass()

    def ensure_repo(self) -> git.Repo:
        if self._repo is not None:
            return self._repo
        if self._repo_dir.exists():
            if (self._repo_dir / ".git").exists():
                self._repo = git.Repo(self._repo_dir)
                self._ensure_origin_url(self._repo)
                return self._repo
            if any(self._repo_dir.iterdir()):
                raise RuntimeError(
                    f"Existing directory {self._repo_dir} is not a Git repository"
                )
            self._repo_dir.rmdir()

        self._repo_dir.parent.mkdir(parents=True, exist_ok=True)
        _LOGGER.info("Cloning %s", redact_url(self._options.repo_url))
        clone_kwargs: dict[str, object] = {"branch": self._options.branch}
        if self._depth_arg:
            clone_kwargs["depth"] = self._depth_arg
        env = self._git_env()
        if env:
            clone_kwargs["env"] = env
        self._repo = git.Repo.clone_from(
            self._options.repo_url,
            self._repo_dir,
            **clone_kwargs,
        )
        self._ensure_origin_url(self._repo)
        return self._repo

    @property
    def _depth_arg(self) -> int | None:
        return None if self._options.git_depth == 0 else self._options.git_depth

    def _git_env(self) -> dict[str, str]:
        env: dict[str, str] = {}
        token = self._options.access_token or os.getenv("GIT_ACCESS_TOKEN")
        if not token:
            return env

        if not self._options.repo_url.startswith("https://"):
            return env

        self._preflight_askpass()
        askpass = self._askpass_path()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = str(askpass)
        env["GIT_UPDATE_ACCESS_TOKEN"] = token
        env["GIT_UPDATE_GIT_USERNAME"] = "x-access-token"
        return env

    def _preflight_askpass(self) -> None:
        if self._askpass_preflight_done:
            return
        self._askpass_preflight_done = True

        token = self._options.access_token or os.getenv("GIT_ACCESS_TOKEN")
        if not token:
            return

        if not self._options.repo_url.startswith("https://"):
            return

        askpass = self._askpass_path()
        if not askpass.exists():
            raise RuntimeError(f"Missing GIT_ASKPASS helper: {askpass}")

        # Ensure executable bit where possible.
        if not os.access(askpass, os.X_OK):
            try:
                os.chmod(askpass, 0o700)
            except OSError:
                pass
        if not os.access(askpass, os.X_OK):
            raise RuntimeError(f"GIT_ASKPASS helper is not executable: {askpass}")

        # Verify the helper can run and returns a username/password without logging secrets.
        base_env = os.environ.copy()
        base_env["GIT_UPDATE_GIT_USERNAME"] = "x-access-token"
        base_env["GIT_UPDATE_ACCESS_TOKEN"] = "x"
        try:
            username = subprocess.run(
                [str(askpass), "Username for 'https://github.com':"],
                check=True,
                capture_output=True,
                text=True,
                env=base_env,
            ).stdout.strip()
            if not username:
                raise RuntimeError("GIT_ASKPASS helper returned empty username")

            password = subprocess.run(
                [str(askpass), "Password for 'https://github.com':"],
                check=True,
                capture_output=True,
                text=True,
                env=base_env,
            ).stdout
            if not password:
                raise RuntimeError("GIT_ASKPASS helper returned empty password")
        except OSError as exc:
            raise RuntimeError(f"Failed to execute GIT_ASKPASS helper: {askpass}") from exc

    @staticmethod
    def _askpass_path() -> Path:
        """Return path to the bundled askpass helper.

        Avoid /data mounts here: HA add-on data volumes can be mounted with noexec,
        which prevents Git from executing helpers stored under /data/state.
        """
        script_path = Path(__file__).resolve().with_name("git_askpass.py")
        try:
            os.chmod(script_path, 0o700)
        except OSError:
            pass
        return script_path

    def _ensure_origin_url(self, repo: git.Repo) -> None:
        try:
            origin = repo.remotes.origin
        except Exception:  # noqa: BLE001
            return
        try:
            if origin.url != self._options.repo_url:
                origin.set_url(self._options.repo_url)
        except Exception:  # noqa: BLE001
            return

    def sync(self) -> GitSyncResult:
        repo = self.ensure_repo()
        before = self._safe_head(repo)
        branch = self._options.branch
        origin = repo.remotes.origin
        fetch_kwargs = {}
        if self._depth_arg:
            fetch_kwargs["depth"] = self._depth_arg
        env = self._git_env()
        if env:
            fetch_kwargs["env"] = env
        origin.fetch(branch, **fetch_kwargs)
        with repo.git.custom_environment(**env):
            repo.git.checkout(branch)
        initial = before is None
        try:
            with repo.git.custom_environment(**env):
                repo.git.pull("--ff-only", "origin", branch)
        except git.GitCommandError:
            _LOGGER.warning(
                "Fast-forward pull failed (divergent branches). Resetting to origin/%s",
                branch,
            )
            origin.fetch(branch, force=True, **fetch_kwargs)
            with repo.git.custom_environment(**env):
                repo.git.reset("--hard", f"origin/{branch}")
        after = self._safe_head(repo)
        if initial and after:
            changes = self._collect_all_files(repo)
        else:
            changes = self._collect_changes(repo, before, after)
        return GitSyncResult(before, after, branch, changes, initial)

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
    def _collect_all_files(repo: git.Repo) -> list[FileChange]:
        tree = repo.git.ls_tree("-r", "HEAD", "--name-only")
        return [
            FileChange(path=line.strip(), change_type="added")
            for line in tree.splitlines()
            if line.strip()
        ]

    @staticmethod
    def _safe_head(repo: git.Repo) -> str | None:
        try:
            return repo.head.commit.hexsha
        except ValueError:
            return None
