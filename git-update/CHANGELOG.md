# Changelog

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
