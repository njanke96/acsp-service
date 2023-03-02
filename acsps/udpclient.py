"""
UDP Client
"""
import asyncio
import logging
import traceback

import acsps.protocol as proto
from acsps.aioudp import open_local_endpoint
from acsps.exceptions import UnsupportedMessageException, MessageParseException

connection_map: dict[int, proto.NewConnection] = dict()


async def udp_loop(bind_addr: str, bind_port: int):
    """
    Coroutine that handles udp messages in a loop.
    """
    local = await open_local_endpoint(bind_addr, bind_port)

    while True:
        try:
            if local.closed:
                local = await open_local_endpoint(bind_addr, bind_port)

            # receive messages
            data, addr = await local.receive()

            try:
                message = proto.parse_acsp_message(data)
            except UnsupportedMessageException as e:
                logging.warning(e)
                continue
            except MessageParseException as e:
                logging.error(e)
                continue
            except Exception as e:
                logging.error(f"Exception {e.__class__}:")
                traceback.print_exc()
                continue

            if isinstance(message, proto.LapCompleted):
                print("Got a LapCompleted:")
                print(f"Car ID: {message.car_id}")
                print(f"Lap Time: {message.laptime}")
                print(f"Cuts: {bool(message.cuts)}")
                print("----")

                if message.car_id in connection_map:
                    pass
                else:
                    logging.error(
                        f"Got a LapCompleted for car id {message.car_id}, "
                        "never got a NewConnection for this car id. Can't record lap."
                    )
            elif isinstance(message, proto.NewConnection):
                # add to connection map
                connection_map[message.car_id] = message
            elif isinstance(message, proto.ConnectionClosed):
                # remove from connection map
                if message.car_id in connection_map:
                    del connection_map[message.car_id]

        except asyncio.CancelledError:
            break

    # not sure if this is actually needed
    local.close()
