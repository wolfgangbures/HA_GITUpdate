# Changelog

## v0.7.5-beta

- Fix error events firing to wrong HA endpoint; deployment and validation failures now correctly fire `{event_name}.error` instead of `{event_name}`.

## v0.7.1

- Add startup preflight check for bundled `git_askpass.py` helper.

## v0.6.5

- Fix `GIT_ASKPASS` helper execution by bundling the script in the image (avoids `/data` noexec mounts and fixes malformed script contents).

## v0.6.4

- Fix HTTPS Git auth for non-interactive containers by using `GIT_ASKPASS` instead of embedding tokens in remote URLs.
- Redact tokens from sync error logs and exposed status.

## v0.6.3
- Added Home Assistant translation metadata so each option shows a friendly label in the UI.
- Rephrased Supervisor 403 warning to clarify that tokens refresh automatically after rebuilding/restarting the add-on.

## v0.6.2
- Clarified Supervisor 403 guidance by explaining permission/token fixes before falling back to HA API.

## v0.6.1
- Request `supervisor_api` permission so Supervisor `/core/check` validation succeeds.
- Bump add-on and API version metadata to align with upstream release numbering.

## v0.3.0
- Added Home Assistant configuration validation after deployment.
- Fire error events when deployment or HA config validation fails.
- Error events use `{event_name}.error` and include error type and message.

## v0.2.0
- Added configurable deployment target path and copy changed files before emitting notifications.
- Validate YAML documents prior to deployment to prevent broken Home Assistant configuration updates.
- Require PyYAML runtime dependency.

## v0.1.1
- Added Home Assistant long-lived token fallback and configurable base URL.
- Included build identifier in startup logs to confirm updates.
- Simplified runtime by running Python service directly on Alpine base image.

## v0.1.0
- Initial scaffold of the Git Update Home Assistant add-on.
- FastAPI service with scheduled Git synchronization and change notifications.
- MQTT optional notifications and Supervisor event emission.
