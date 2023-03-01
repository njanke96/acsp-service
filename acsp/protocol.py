"""
ACSP Protocol Functions
"""
import struct
from enum import IntEnum
from typing import TypeVar, Tuple

from acsp.exceptions import UnsupportedMessageException, MessageParseException

_T = TypeVar("_T")


class ACSPMessage(IntEnum):
    ACSP_ADMIN_COMMAND = 209
    ACSP_BROADCAST_CHAT = 203
    ACSP_CAR_INFO = 54
    ACSP_CAR_UPDATE = 53
    ACSP_CE_COLLISION_WITH_CAR = 10
    ACSP_CE_COLLISION_WITH_ENV = 11
    ACSP_CHAT = 57
    ACSP_CLIENT_EVENT = 130
    ACSP_CLIENT_LOADED = 58
    ACSP_CONNECTION_CLOSED = 52
    ACSP_END_SESSION = 55
    ACSP_ERROR = 60
    ACSP_GET_CAR_INFO = 201
    ACSP_GET_SESSION_INFO = 204
    ACSP_KICK_USER = 206
    ACSP_LAP_COMPLETED = 73
    ACSP_NEW_CONNECTION = 51
    ACSP_NEW_SESSION = 50
    ACSP_NEXT_SESSION = 207
    ACSP_REALTIMEPOS_INTERVAL = 200
    ACSP_RESTART_SESSION = 208
    ACSP_SEND_CHAT = 202
    ACSP_SESSION_INFO = 59
    ACSP_SET_SESSION_INFO = 205
    ACSP_VERSION = 56


class Vector3f:
    x: float
    y: float
    z: float

    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z


# Outgoing messages

def car_info(car_id: int) -> bytes:
    return bytes([ACSPMessage.ACSP_GET_CAR_INFO, car_id])


# Incoming Messages

class BaseMessage:
    pass


class CarInfo(BaseMessage):
    car_id: int
    is_connected: bool
    model: str
    skin: str
    driver_name: str
    driver_team: str
    guid: str

    def __init__(self, message: bytes):
        data = _parse_struct(
            message,
            _parse_byte,
            _parse_byte,
            _parse_unicode,
            _parse_unicode,
            _parse_unicode,
            _parse_unicode,
            _parse_unicode,
        )

        self.car_id = data[0]
        self.is_connected = data[1]
        self.model = data[2]
        self.skin = data[3]
        self.driver_name = data[4]
        self.driver_team = data[5]
        self.guid = data[6]


class LapCompleted(BaseMessage):
    car_id: int
    laptime: int
    cuts: int

    # TODO: leaderboard array, grip

    def __init__(self, message: bytes):
        data = _parse_struct(message, _parse_byte, _parse_int32, _parse_byte)
        self.car_id = data[0]
        self.laptime = data[1]
        self.cuts = data[2]


# Incoming message parsing

def parse_acsp_message(raw_message: bytes) -> _T | None:
    # message type (first byte)
    try:
        msg_type = ACSPMessage(raw_message[0])
    except ValueError:
        return None

    msg = raw_message[1:]

    try:
        return {
            ACSPMessage.ACSP_LAP_COMPLETED: LapCompleted,
            ACSPMessage.ACSP_CAR_INFO: CarInfo,
        }.get(msg_type)(msg)
    except KeyError:
        raise UnsupportedMessageException(int(msg_type))


_ParserReturn = Tuple[_T, int]


def _parse_byte(chunk: bytes) -> _ParserReturn[int]:
    return chunk[0], 1


def _parse_short(chunk: bytes) -> _ParserReturn[int]:
    return int.from_bytes(chunk[:2], byteorder="big", signed=False), 2


def _parse_int32(chunk: bytes) -> _ParserReturn[int]:
    return int.from_bytes(chunk[:4], byteorder="big", signed=False), 4


def _parse_float(chunk: bytes) -> _ParserReturn[float]:
    try:
        return struct.unpack(">f", chunk[:4])[0], 4
    except struct.error:
        raise MessageParseException(f"Could not unpack to float: {chunk}")


def _parse_vector3xfloat(chunk: bytes) -> _ParserReturn[Vector3f]:
    try:
        x = struct.unpack(">f", chunk[:4])[0]
        y = struct.unpack(">f", chunk[4:8])[0]
        z = struct.unpack(">f", chunk[8:12])[0]
    except struct.error:
        raise MessageParseException(f"Could not unpack to Vector3f: {chunk}")

    return Vector3f(x, y, z), 12


def _parse_string(chunk: bytes) -> _ParserReturn[str]:
    strlen = chunk[0]

    try:
        return chunk[1 : strlen + 1].decode("ascii"), strlen + 1
    except UnicodeDecodeError:
        raise MessageParseException(f"Could not parse as ascii: {chunk}")


def _parse_unicode(chunk: bytes) -> _ParserReturn[str]:
    strlen = chunk[0]

    try:
        return chunk[1 : strlen + 1].decode("utf-32"), strlen + 1
    except UnicodeDecodeError:
        raise MessageParseException(f"Could not parse as utf-32: {chunk}")


def _parse_struct(message: bytes, *parsers) -> list:
    """
    Unpack a message given a UDP payload and some parsers.
    :param message: payload
    :param parsers: parsers returning _ParserReturn
    :return: list of data
    """
    data = []
    slice_ = message
    ptr = 0

    for parser in parsers:
        parsed, inc = parser(slice_)
        data.append(parsed)
        ptr += inc
        slice_ = slice_[ptr:]

    return data
