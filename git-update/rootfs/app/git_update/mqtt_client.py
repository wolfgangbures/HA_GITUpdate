from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import paho.mqtt.client as mqtt

from .config import MqttSettings

_LOGGER = logging.getLogger(__name__)


@dataclass
class MqttPayload:
    topic: str
    payload: dict[str, Any]
    qos: int = 1
    retain: bool = False


class MqttPublisher:
    def __init__(self, settings: MqttSettings) -> None:
        self._settings = settings

    async def publish(self, payload: MqttPayload) -> None:
        if not self._settings.enabled:
            return
        await asyncio.to_thread(self._publish_sync, payload)

    def _publish_sync(self, payload: MqttPayload) -> None:
        client = mqtt.Client()
        if self._settings.username:
            client.username_pw_set(self._settings.username, self._settings.password)
        try:
            client.connect(self._settings.host, self._settings.port, keepalive=30)
            client.publish(
                payload.topic,
                json_dumps(payload.payload),
                qos=payload.qos,
                retain=payload.retain,
            )
            client.disconnect()
            _LOGGER.debug("Published MQTT message to %s", payload.topic)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Failed to publish MQTT message: %s", exc)


def json_dumps(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data, separators=(",", ":"))
