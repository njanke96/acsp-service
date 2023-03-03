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
from acsps.database.queries import record_lap_pr, compare_to_server_record
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

    logging.info(f"UDP Listening on {bind_addr}:{bind_port}")
    while True:

        try:
            if local.closed:
                local = await open_local_endpoint(bind_addr, bind_port)

            # receive messages
            data, addr = await local.receive()

            message = proto.parse_acsp_message(data)

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
                            sr_diff = await compare_to_server_record(
                                db,
                                session_data.track_name,
                                session_data.track_config,
                                connection.car_model,
                                message.laptime
                            )

                            result_diff = await record_lap_pr(
                                db,
                                driver_guid=connection.driver_guid,
                                track_name=session_data.track_name,
                                track_config=session_data.track_config,
                                driver_name=connection.driver_name,
                                lap_time_ms=message.laptime,
                                car_model=connection.car_model,
                                grip_level=message.grip_level,
                            )

                            lap_time_formatted = format_ms_time(message.laptime)
                            diff_formatted_abs = format_ms_time(abs(result_diff))
                            sr_diff_formatted_abs = format_ms_time(abs(sr_diff))

                            if result_diff == message.laptime:
                                # first recorded lap
                                msg = proto.send_message(
                                    message.car_id,
                                    f"You set your first PB for the current track & car with time {lap_time_formatted}"
                                )

                                local.send(msg, addr)
                            elif result_diff < 0:
                                # new pb
                                logging.info(
                                    f"{connection.driver_name} set a new personal best on {session_data.track_name}/"
                                    f"{session_data.track_config} with time {lap_time_formatted} "
                                    f"(-{diff_formatted_abs})"
                                )

                                broadcast_msg = proto.broadcast_message(
                                    f"{connection.driver_name} set a new PB of {lap_time_formatted} "
                                    f"(-{diff_formatted_abs}) for the {connection.car_model} on this track."
                                )

                                local.send(broadcast_msg, addr)
                            else:
                                # did not beat pb
                                msg = proto.send_message(
                                    message.car_id,
                                    f"Lap time: {lap_time_formatted} (PB +{diff_formatted_abs})"
                                )

                                local.send(msg, addr)

                            # server record

                            if sr_diff == message.laptime:
                                logging.info(
                                    f"{connection.driver_name} set the first server record on "
                                    f"{session_data.track_name}/{session_data.track_config} with time "
                                    f"{lap_time_formatted}"
                                )

                                broadcast_msg = proto.broadcast_message(
                                    f"{connection.driver_name} set the first server record for the "
                                    f"{connection.car_model} on this track with time {lap_time_formatted}"
                                )

                                local.send(broadcast_msg, addr)
                            elif sr_diff < 0:
                                logging.info(
                                    f"{connection.driver_name} set a new server record on {session_data.track_name}/"
                                    f"{session_data.track_config} with time {lap_time_formatted} "
                                    f"(-{sr_diff_formatted_abs})"
                                )

                                broadcast_msg = proto.broadcast_message(
                                    f"{connection.driver_name} beat the server record for the "
                                    f"{connection.car_model} on this track with time {lap_time_formatted} "
                                    f"(Beat previous SR by {sr_diff_formatted_abs})."
                                )

                                local.send(broadcast_msg, addr)
                            else:
                                # did not beat sr
                                msg = proto.send_message(
                                    message.car_id,
                                    f"Server record diff: +{sr_diff_formatted_abs})"
                                )

                                local.send(msg, addr)
                    else:
                        logging.error(f"No session data. Can't record lap for car {message.car_id}")
                else:
                    logging.error(f"No connection info for car {message.car_id}")
            elif isinstance(message, proto.NewConnection):
                # add to connection map
                connection_map[message.car_id] = message
                logging.info(
                    f"New Connection: car {message.car_id} driven "
                    f"by {message.driver_name} ({message.driver_guid})"
                )
            elif isinstance(message, proto.ConnectionClosed):
                # remove from connection map
                if message.car_id in connection_map:
                    del connection_map[message.car_id]
                logging.info(
                    f"Closed Connection: car {message.car_id} no longer "
                    f"driven by {message.driver_name} ({message.driver_guid})"
                )
            elif isinstance(message, proto.NewSession):
                session_data.track_name = message.track_name
                session_data.track_config = message.track_config
                logging.info(f"Session starting: {session_data.track_name}/{session_data.track_config}")

        except UnsupportedMessageException as e:
            logging.warning(e)
            continue
        except MessageParseException as e:
            logging.error(e)
            continue
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Exception in UDP client loop: {e.__class__}:")
            traceback.print_exc()
            continue

    # not sure if this is actually needed
    local.close()
