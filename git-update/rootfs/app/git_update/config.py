from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, PositiveInt, ValidationError

OPTIONS_PATH = Path(os.getenv("ADDON_OPTIONS_FILE", "/data/options.json"))
LOCAL_DEV_OPTIONS = Path("./dev/options.json")
STATE_DIR = Path(os.getenv("GIT_UPDATE_STATE_DIR", "/data/state"))
REPO_DIR = Path(os.getenv("GIT_UPDATE_REPO_DIR", "/data/repo"))
DEFAULT_HTTP_PORT = 7999


class MqttSettings(BaseModel):
    enabled: bool = False
    host: str = "core-mosquitto"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    topic: str = "homeassistant/git_update"
    qos: int = Field(default=1, ge=0, le=2)
    retain: bool = False


class Options(BaseModel):
    repo_url: str
    branch: str = "main"
    access_token: str | None = None
    ha_access_token: str | None = None
    ha_base_url: str | None = None
    ha_verify_ssl: bool = True
    target_path: str = "/config"
    poll_interval: PositiveInt = 300
    git_depth: int = Field(default=1, ge=0)
    ha_event_name: str = "git_update.files_changed"
    notify_on_startup: bool = True
    verify_ssl: bool = True
    log_level: str = Field(default="info", pattern=r"^(trace|debug|info|warning|error)$")
    http_api_port: int = DEFAULT_HTTP_PORT
    mqtt_enabled: bool = False
    mqtt_topic: str = "homeassistant/git_update"
    mqtt_host: str | None = None
    mqtt_port: int | None = None
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_qos: int | None = None
    mqtt_retain: bool = False

    def mqtt(self) -> MqttSettings:
        return MqttSettings(
            enabled=self.mqtt_enabled,
            host=self.mqtt_host or "core-mosquitto",
            port=self.mqtt_port or 1883,
            username=self.mqtt_username,
            password=self.mqtt_password,
            topic=self.mqtt_topic,
            qos=self.mqtt_qos if self.mqtt_qos is not None else 1,
            retain=self.mqtt_retain,
        )


def _load_raw_options() -> dict[str, Any]:
    candidates = [OPTIONS_PATH, LOCAL_DEV_OPTIONS]
    for candidate in candidates:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                return json.load(handle)
    raise FileNotFoundError(
        "No options file found. Provide /data/options.json or ./dev/options.json"
    )


def load_options() -> Options:
    raw = _load_raw_options()
    try:
        return Options(**raw)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid options: {exc}") from exc
