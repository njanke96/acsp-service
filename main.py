import asyncio
import logging
import signal

from acsps.udpclient import udp_loop
from acsps.database.main import create_database_tables

logging.root.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, format="%(levelname)s : %(message)s")


async def shutdown(sig, loop_):
    logging.info(f"Received exit signal {sig.name}...")
    logging.info("Shutting down...")

    tasks = asyncio.all_tasks()
    [task.cancel() for task in tasks]

    loop_.stop()


def main():
    create_database_tables()

    loop = asyncio.new_event_loop()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(s, lambda sig=s: asyncio.create_task(shutdown(sig, loop)))

    try:
        loop.create_task(udp_loop("0.0.0.0", 11200))
        loop.run_forever()
    finally:
        loop.close()
        logging.info("Shutdown complete.")


if __name__ == "__main__":
    main()
