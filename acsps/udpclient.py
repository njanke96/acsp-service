"""
UDP Client
"""
import asyncio
import logging
import traceback

import acsps.protocol as proto
from acsps.aioudp import open_local_endpoint
from acsps.common import format_ms_time
from acsps.database.main import database
from acsps.database.queries import record_lap_pr
from acsps.exceptions import UnsupportedMessageException, MessageParseException

connection_map: dict[int, proto.NewConnection] = dict()


class _SessionData:
    def __init__(self):
        self.track_name = None
        self.track_config = None


session_data = _SessionData()


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
                # ignore cut laps
                if message.cuts:
                    logging.info(f"Ignoring cut lap from car {message.car_id}")
                    continue

                # record lap pr if all required data is available
                if message.car_id in connection_map:
                    connection = connection_map[message.car_id]
                    if (
                        session_data.track_name is not None
                        and session_data.track_config is not None
                    ):
                        async with database.acquire() as db:
                            result = await record_lap_pr(
                                db,
                                driver_guid=connection.driver_guid,
                                track_name=session_data.track_name,
                                track_config=session_data.track_config,
                                driver_name=connection.driver_name,
                                lap_time_ms=message.laptime,
                                car_model=connection.car_model,
                                grip_level=1.0,
                            )

                            if result:
                                lap_time_formatted = format_ms_time(message.laptime)
                                logging.info(
                                    f"{connection.driver_name} set a new personal best on {session_data.track_name}/"
                                    f"{session_data.track_config} with time {lap_time_formatted}"
                                )

                                broadcast_msg = proto.broadcast_message(
                                    f"{connection.driver_name} set a new PB of {lap_time_formatted}"
                                )

                                await local.send(broadcast_msg, addr)
            elif isinstance(message, proto.NewConnection):
                # add to connection map
                connection_map[message.car_id] = message
            elif isinstance(message, proto.ConnectionClosed):
                # remove from connection map
                if message.car_id in connection_map:
                    del connection_map[message.car_id]
            elif isinstance(message, proto.NewSession):
                session_data.track_name = message.track_name
                session_data.track_config = message.track_config

        except asyncio.CancelledError:
            break

    # not sure if this is actually needed
    local.close()
