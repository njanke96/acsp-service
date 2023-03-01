"""
UDP Client
"""
import asyncio
import logging
import traceback

from acsp.protocol import parse_acsp_message, LapCompleted, CarInfo
from acsp.aioudp import open_local_endpoint
from acsp.exceptions import UnsupportedMessageException, MessageParseException


async def udp_loop(bind_addr: str, bind_port: int):
    local = await open_local_endpoint(bind_addr, bind_port)

    while True:
        try:
            # receive messages
            data, addr = await local.receive()

            try:
                message = parse_acsp_message(data)
            except UnsupportedMessageException as e:
                logging.debug(e)
                continue
            except MessageParseException as e:
                logging.warning(e)
                continue
            except Exception as e:
                logging.error(f"Exception {e.__class__}:")
                traceback.print_exc()
                continue

            if isinstance(message, LapCompleted):
                print("Got a LapCompleted:")
                print(f"Car ID: {message.car_id}")
                print(f"Lap Time: {message.laptime}")
                print(f"Cuts: {message.cuts}")
                print("----")
            elif isinstance(message, CarInfo):
                pass
        except asyncio.CancelledError:
            break

    # not sure if this is actually needed
    local.close()
