# Git Update AI Guide

## Architecture Snapshot
- The async scheduler + HTTP server live in [git-update/rootfs/app/main.py](git-update/rootfs/app/main.py); `GitUpdateService` in [git-update/rootfs/app/git_update/service.py](git-update/rootfs/app/git_update/service.py) owns the poll loop, locking, and status tracking.
- Git operations stay inside [git-update/rootfs/app/git_update/git_client.py](git-update/rootfs/app/git_update/git_client.py) using GitPython with `depth`-aware fetches and fast-forward pulls; divergence triggers a hard reset to `origin/<branch>`.
- File deployment + YAML validation happens in [git-update/rootfs/app/git_update/deployer.py](git-update/rootfs/app/git_update/deployer.py), which enforces path guards between the repo checkout (`/data/repo` by default) and the target Home Assistant config path.
- Notifications are funneled through [git-update/rootfs/app/git_update/notifier.py](git-update/rootfs/app/git_update/notifier.py), combining Home Assistant events ([git-update/rootfs/app/git_update/ha_events.py](git-update/rootfs/app/git_update/ha_events.py)) and optional MQTT messages ([git-update/rootfs/app/git_update/mqtt_client.py](git-update/rootfs/app/git_update/mqtt_client.py)).

## Runtime & Configuration
- Options are defined once in [git-update/rootfs/app/git_update/config.py](git-update/rootfs/app/git_update/config.py); always add new fields to `Options`, surface them in `git-update/config.json`, and mirror defaults in `dev/options.json`.
- `load_options()` reads `/data/options.json` (override via `ADDON_OPTIONS_FILE`) and falls back to `./dev/options.json`. Local runs can redirect state paths with `GIT_UPDATE_STATE_DIR` and `GIT_UPDATE_REPO_DIR`.
- Secrets (`access_token`, `ha_access_token`, `mqtt_password`) are stripped before serving `/config`; keep sensitive data inside `Options` and never log them.

## Service Flow
- `GitUpdateService.run()` triggers an optional startup sync, then loops every `poll_interval` seconds. Use `trigger_sync("manual")` from the FastAPI `/sync` endpoint to force a run.
- `GitRepoManager.sync()` returns a typed change list (`FileChange`/`SyncMetadata` in [git-update/rootfs/app/git_update/models.py](git-update/rootfs/app/git_update/models.py)); only manipulate repo state through this class to honor shallow clones and auth rewriting.
- `FileDeployer` copies/renames/deletes files relative to `target_path`, validating `.yml/.yaml` via `yaml.safe_load`. Deployment issues raise `DeploymentError` and produce `.error` notifications.
- After deployment, `HAEventClient.check_config()` calls `/core/check` (Supervisor token) or `/api/services/homeassistant/check_config` (long-lived token). Respect the `(bool | None, str | None)` contract: `None` means validation skipped and should not block notifications.

## HTTP & Observability
- The FastAPI app in [git-update/rootfs/app/git_update/api.py](git-update/rootfs/app/git_update/api.py) exposes `/health`, `/status`, `/sync`, and `/config`. Keep new endpoints idempotent and return Pydantic models so the Supervisor panel stays serializable.
- `StatusResponse` is the single source of truth for UI/CLI consumers; update it whenever sync state changes.
- Logging is configured in `main.py` and respects the `log_level` option. Use structured `logger.info("message | key=%s", value)` style for new logs to remain searchable in HA Supervisor.

## Local Development
- Requirements live in [git-update/rootfs/app/requirements.txt](git-update/rootfs/app/requirements.txt); use Python 3.12+ (`pip install -r ...`). Some dependencies (e.g., `uvicorn[standard]`, `httpx`) pull in native libs, so ensure a Rust toolchain is available when installing on Windows.
- Typical workflow: (1) create `dev/options.json` matching the add-on schema, (2) set `ADDON_OPTIONS_FILE=dev/options.json`, (3) run `python git-update/rootfs/app/main.py` for the scheduler + HTTP API, (4) hit `POST /sync` for manual tests via `curl http://localhost:7999/sync -d '{"reason":"manual"}'`.
- When changing schema or container behavior, also adjust [git-update/config.json](git-update/config.json), the add-on docs in [git-update/README.md](git-update/README.md), and `build.yaml`/`Dockerfile` as needed.

## Integration Notes
- Events default to `git_update.files_changed`; errors append `.error`. Keep payloads backwards compatible because automations likely parse `changes[].change_type`.
- MQTT publishing is optional; respect `Options.mqtt()` to inherit broker defaults. Publish success to `topic` and errors to `topic/error` as in `Notifier`.
- Home Assistant access: prefer Supervisor token injection (`homeassistant_api: true`, `supervisor_api: true`). If unavailable, document the need for `ha_access_token` and set `ha_base_url`/`ha_verify_ssl` accordingly.

## Outstanding Setup Checklist
- Launching end-to-end inside Docker/HA remains **blocked** until a local Python 3.12 environment plus the Rust toolchain are installed (needed for dependency builds). All other scaffold steps are complete; rerun the add-on once those prerequisites exist.

- Work through each checklist item systematically.
- Keep communication concise and focused.
- Follow development best practices.


## GitHub
- Always split branches by feature/fix for PRs; avoid working directly on `main`.
- Write clear, descriptive commit messages; reference related issues/PRs when applicable.
- Create PRs with me as approver.
- **ALWAYS create beta releases first** (e.g., v0.7.3-beta) using `--prerelease` flag before creating stable releases.
- Only create stable releases after beta has been tested and approved.
- Tag releases in GitHub matching the version in `config.json`.
- Increment the version in `config.json` for every PR that changes functionality.