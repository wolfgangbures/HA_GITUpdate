# Changelog

## v0.1.1
- Added Home Assistant long-lived token fallback and configurable base URL.
- Included build identifier in startup logs to confirm updates.
- Simplified runtime by running Python service directly on Alpine base image.

## v0.1.0
- Initial scaffold of the Git Update Home Assistant add-on.
- FastAPI service with scheduled Git synchronization and change notifications.
- MQTT optional notifications and Supervisor event emission.
