from __future__ import annotations

import asyncio
import logging
import os
import signal

import uvicorn

from git_update.api import create_app
from git_update.config import load_options
from git_update.service import GitUpdateService

__VERSION__ = "0.6.1"


async def main() -> None:
    options = load_options()
    log_level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    logging.basicConfig(
        level=log_level_map.get(options.log_level.lower(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    
    service = GitUpdateService(options)
    build_version = os.getenv("ADDON_BUILD_VERSION", "dev")
    logging.getLogger(__name__).info(
        "Git Update service starting | version=%s | build=%s | repo=%s | branch=%s",
        __VERSION__,
        build_version,
        service.options.repo_url,
        service.options.branch,
    )
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
