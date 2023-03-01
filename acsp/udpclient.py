"""
UDP Client
"""
import asyncio
import logging
import traceback

from acsp.protocol import parse_acsp_message, LapCompleted, CarInfo, car_info_request
from acsp.aioudp import open_local_endpoint, open_remote_endpoint
from acsp.exceptions import UnsupportedMessageException, MessageParseException

UDP_TIMEOUT = 5

lap_events_waiting: dict[int, LapCompleted] = dict()


async def request_car_info_for_lap(lap_event: LapCompleted, addr: tuple[str, int]):
    payload = car_info_request(lap_event.car_id)

    try:
        async with asyncio.timeout(UDP_TIMEOUT):
            remote = await open_remote_endpoint(*addr)
            remote.send(payload)
    except asyncio.TimeoutError:
        raise RuntimeError("Timed out requesting car info!")

    lap_events_waiting[lap_event.car_id] = lap_event


async def udp_loop(bind_addr: str, bind_port: int, event_loop: asyncio.AbstractEventLoop):
    """Main udp loop coro"""
    local = await open_local_endpoint(bind_addr, bind_port)

    while True:
        try:
            if local.closed:
                local = await open_local_endpoint(bind_addr, bind_port)

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
                print(f"Cuts: {bool(message.cuts)}")
                print("----")

                # car info request
                await request_car_info_for_lap(message, addr)

            elif isinstance(message, CarInfo):
                print("Got a CarInfo:")
                print(f"Car ID: {message.car_id}")
                print(f"Driver ID: {message.guid}")
                print(f"GUID: {message.guid}")

                if message.car_id in lap_events_waiting:
                    print("We were waiting for this info, process the lap completed event.")
                    del lap_events_waiting[message.car_id]
        except asyncio.CancelledError:
            break

    # not sure if this is actually needed
    local.close()
