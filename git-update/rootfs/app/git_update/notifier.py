from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence

from .config import Options
from .ha_events import HAEventClient
from .models import FileChange
from .mqtt_client import MqttPayload, MqttPublisher

_LOGGER = logging.getLogger(__name__)


class Notifier:
    def __init__(self, options: Options) -> None:
        self._options = options
        self._ha = HAEventClient(options.ha_event_name)
        self._mqtt_settings = options.mqtt()
        self._mqtt = MqttPublisher(self._mqtt_settings)

    async def notify(
        self,
        changes: Sequence[FileChange],
        branch: str,
        commit: str | None,
        reason: str,
    ) -> None:
        payload = {
            "event": self._options.ha_event_name,
            "branch": branch,
            "commit": commit,
            "reason": reason,
            "changes": [change.model_dump() for change in changes],
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._ha.fire_event(payload)
        await self._mqtt.publish(
            MqttPayload(
                topic=self._mqtt_settings.topic,
                payload=payload,
                qos=self._mqtt_settings.qos,
                retain=self._mqtt_settings.retain,
            )
        )

    async def aclose(self) -> None:
        await self._ha.aclose()
