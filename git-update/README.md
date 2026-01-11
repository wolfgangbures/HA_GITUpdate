# Git Update Add-on

Git Update keeps a local clone of a Git repository inside Home Assistant and surfaces file change notifications.

## Configuration
| Option | Description |
| ------ | ----------- |
| `repo_url` *(required)* | HTTPS or SSH URL of the repository to follow. |
| `branch` | Branch or ref to check out. Defaults to `main`. |
| `access_token` | Token injected into HTTPS URLs for private repositories. Leave blank for anonymous access. |
| `ha_access_token` | Optional long-lived Home Assistant token when Supervisor token is unavailable. |
| `ha_base_url` | Base URL used when emitting events with `ha_access_token` (e.g. `http://homeassistant:8123`). |
| `ha_verify_ssl` | Whether to verify TLS certificates when using `ha_base_url`. |
| `target_path` | Root directory where changed files are copied (defaults to `/config`). |
| `poll_interval` | Sync interval in seconds (minimum 60 recommended). |
| `git_depth` | Shallow-clone depth. Set to `0` for full history. |
| `ha_event_name` | Supervisor event fired after changes are discovered. |
| `notify_on_startup` | Emit a notification after the first successful sync. |
| `verify_ssl` | Toggle TLS verification for HTTPS remotes. |
| `log_level` | Logging verbosity (`debug`, `info`, `warning`, `error`). |
| `mqtt_enabled` | Publish change payloads to MQTT. |
| `mqtt_topic` | MQTT topic for change payloads. |
| `mqtt_host`, `mqtt_port` | Broker connection overrides (defaults to `core-mosquitto:1883`). |
| `mqtt_username`, `mqtt_password` | Credentials when anonymous access is disabled. |
| `mqtt_qos`, `mqtt_retain` | Delivery controls for MQTT messages. |
| `http_api_port` | Exposes the management REST API. Disable (set to `0`) to turn off the listener. |

> Ensure the add-on manifest includes `homeassistant_api: true` so the Supervisor injects `SUPERVISOR_TOKEN`. If your environment does not provide that token, set `ha_access_token` to a long-lived access token created in your Home Assistant user profile.

All YAML files are validated before deployment. Invalid documents block the notification and surface the parser error in the add-on logs.

After deployment, Home Assistant configuration is validated via the Supervisor `/core/check` endpoint (equivalent to `ha core check`) whenever the add-on runs under Home Assistant OS/Supervisor, so we wait for the final outcome before emitting success events. In standalone installs we fall back to the legacy `check_config` service. If validation fails, an error event is fired instead of the success notification.

## Events

### Success Event: `{ha_event_name}`
Fired after successful sync, deployment, and HA config validation.

Payload:
```json
{
  "event": "git_update.files_changed",
  "branch": "main",
  "commit": "abc123",
  "reason": "scheduled",
  "changes": [{"path": "config.yaml", "change_type": "modified"}],
  "synced_at": "2026-01-09T12:00:00Z"
}
```

### Error Event: `{ha_event_name}.error`
Fired when deployment or HA config validation fails.

Payload:
```json
{
  "event": "git_update.files_changed.error",
  "error_type": "config_validation_error",
  "error_message": "Home Assistant configuration invalid: ...",
  "branch": "main",
  "commit": "abc123",
  "timestamp": "2026-01-09T12:00:00Z"
}
```

## Deployment Flow
- The repository is cloned into the add-on data directory (`/data/repo`).
- After each sync, changed files are copied into `target_path` (default `/config`).
- Deletions and renames are mirrored, removing obsolete files in the destination.
- Only after a successful deployment are Home Assistant events and MQTT messages emitted.

### MQTT Payload
```json
{
  "event": "git_update.files_changed",
  "commit": "abc123",
  "branch": "main",
  "changes": [
    {"path": "custom_components/example/__init__.py", "change_type": "modified"}
  ],
  "synced_at": "2026-01-06T12:00:00Z"
}
```

## API Endpoints
| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/health` | Liveness probe. |
| `GET` | `/status` | Returns last sync metadata and outstanding errors. |
| `POST` | `/sync` | Immediately triggers a sync (body optional `{ "reason": "manual" }`). |
| `GET` | `/config` | Shows the effective runtime configuration minus secrets. |

## Local Development
1. Install Python 3.12 and create a virtual environment.
2. Install requirements from `rootfs/app/requirements.txt`.
3. Create `dev/options.json` that mirrors the add-on schema, including a writable `target_path`.
4. Run `python git-update/rootfs/app/main.py` to start the scheduler and API locally.

## Release Process
1. Update `CHANGELOG.md` with highlights.
2. Bump `version` in `config.json`.
3. Tag the release in Git (`git tag v0.1.0`).
4. Build multi-arch images using the Home Assistant add-on builder or GitHub Actions.
