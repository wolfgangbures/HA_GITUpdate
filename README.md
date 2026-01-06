# Git-Update Home Assistant Add-on

Git-Update is a Home Assistant add-on that keeps a local working copy of any Git repository synchronized and notifies Home Assistant whenever files change. The add-on exposes a lightweight HTTP API, emits Home Assistant events by default, and can optionally publish MQTT messages for additional automations.

## Features
- Scheduled Git fetch + pull with configurable interval and shallow clone depth
- Hash-based change detection with per-file change types (added/modified/deleted/renamed)
- Home Assistant event emission via the Supervisor Core API (default)
- Optional MQTT notifications with configurable topic, QoS, and credentials
- On-demand sync and status endpoints exposed through FastAPI
- Supervisor-friendly logging with structured context for observability

## Repository Layout
- `repository.json` – metadata describing this add-on repository for Home Assistant
- `git-update/` – the add-on itself (Dockerfile, config, docs, root filesystem)
  - `config.json` – options schema and default values exposed to Home Assistant
  - `build.yaml` – multi-architecture build definition
  - `rootfs/` – files copied into the add-on container (service scripts + Python app)

## Quick Start
1. Add this Git repository URL to **Settings → Add-ons → Add-on Store → Repositories** in Home Assistant.
2. Install **Git Update** from the store.
3. Configure required options (at minimum `repo_url`).
4. Start the add-on; monitor logs for sync status and triggered events.

## Configuration Summary
| Option | Description | Default |
| ------ | ----------- | ------- |
| `repo_url` | Git repository to mirror | `https://github.com/home-assistant/core.git` |
| `branch` | Branch or ref to track | `main` |
| `access_token` | Personal access token for private repos | empty |
| `poll_interval` | Sync interval in seconds | `300` |
| `ha_event_name` | Event name fired via Supervisor| `git_update.files_changed` |
| `notify_on_startup` | Emit notification after first sync | `true` |
| `mqtt_enabled` | Toggle MQTT notifications | `false` |
| `mqtt_topic` | Topic to publish change payloads | `homeassistant/git_update` |

See `git-update/README.md` for the full option schema with MQTT credentials, SSL verification, and log level controls.

## Development
1. Clone the repo and enter the workspace.
2. Install development dependencies (Python 3.12 recommended):
   ```bash
   pip install -r git-update/rootfs/app/requirements.txt
   ```
3. Copy `dev/options.json` (to be created) into `/data/options.json` when running locally or export `ADDON_DEV_OPTIONS` pointing to a JSON file. The Python service automatically falls back to `./dev/options.json` for local runs. You can override the default `/data` directories by setting `GIT_UPDATE_STATE_DIR` and `GIT_UPDATE_REPO_DIR` to any writable path on your workstation.
4. Run the service locally:
   ```bash
   uvicorn git_update.api:create_app --reload --port 7999
   ```
   Start `python git-update/rootfs/app/main.py` in another terminal to simulate the scheduled sync loop.

## GitHub Repository
Once you are ready to publish:
1. Initialize Git: `git init && git add . && git commit -m "Initial scaffold"`.
2. Create (or reuse) the `HA_GITUpdate` repository on GitHub.
3. Link remotes and push:
   ```bash
   git branch -M main
   git remote add origin https://github.com/wolfgangbures/HA_GITUpdate.git
   git push -u origin main
   ```

## License
Project license to be determined. Update `LICENSE` if you adopt Apache-2.0, MIT, or another license.
