from __future__ import annotations

import asyncio
import logging
import os
import signal

import uvicorn

from git_update.api import create_app
from git_update.service import GitUpdateService

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


async def main() -> None:
    service = GitUpdateService()
    app = create_app(service)
    http_port = service.options.http_api_port
    server: uvicorn.Server | None = None
    if http_port > 0:
        config = uvicorn.Config(app, host="0.0.0.0", port=http_port, log_level="info")
        server = uvicorn.Server(config)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown_signal() -> None:
        if server:
            server.should_exit = True
        loop.create_task(service.shutdown())
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown_signal)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(service.run())
        if server:
            tg.create_task(server.serve())
        tg.create_task(stop_event.wait())


if __name__ == "__main__":
    asyncio.run(main())
