"""
UDP Client
"""
import asyncio

from acsp.acsp import parse_acsp_message, LapCompleted, CarInfo
from acsp.aioudp import open_local_endpoint


async def udp_loop(bind_addr: str, bind_port: int):
    local = await open_local_endpoint(bind_addr, bind_port)

    while True:
        try:
            # receive messages
            data, addr = await local.receive()
            message = parse_acsp_message(data)

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
