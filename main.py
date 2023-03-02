import asyncio
import logging
import signal

import uvicorn
import uvicorn.logging

import acsps.env
from acsps.udpclient import udp_loop
from acsps.database.main import create_database_tables
from acsps.webapi.app import app

logging_fmt = "%(levelname)s:%(name)s:%(message)s"   # the default
logging_fmt_uvicorn = "%(levelname)s:uvicorn:%(message)s"

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.name = "acsps"
root_handler = root_logger.handlers[0]
root_handler.setFormatter(logging.Formatter(logging_fmt))


class ServerWithoutSigHandlers(uvicorn.Server):
    def install_signal_handlers(self):
        pass


async def shutdown(sig, loop_):
    logging.info(f"Received exit signal {sig.name}...")
    logging.info("Shutting down...")

    tasks = asyncio.all_tasks()
    [task.cancel() for task in tasks]

    loop_.stop()


async def uvicorn_task():
    conf = uvicorn.Config(
        app,
        host=acsps.env.ACSPS_WEB_ADDR,
        port=int(acsps.env.ACSPS_WEB_PORT),
        access_log=False,
    )

    logger = logging.getLogger("uvicorn")
    logger.handlers[0].setFormatter(logging.Formatter(logging_fmt_uvicorn))

    server = ServerWithoutSigHandlers(conf)
    await server.serve()


def main():
    create_database_tables()

    loop = asyncio.new_event_loop()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda sig=s: asyncio.create_task(shutdown(sig, loop))
        )

    try:
        loop.create_task(udp_loop(acsps.env.ACSPS_UDP_ADDR, int(acsps.env.ACSPS_UDP_PORT)))
        loop.create_task(uvicorn_task())
        loop.run_forever()
    finally:
        loop.close()
        logging.info("Shutdown complete.")


if __name__ == "__main__":
    main()
