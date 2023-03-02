"""
ACSP Protocol Functions
"""
import struct
from enum import IntEnum
from typing import TypeVar, Tuple, Callable

from acsps.exceptions import UnsupportedMessageException, MessageParseException

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


# Outgoing message functions


def broadcast_message(message: str) -> bytes:
    unicode_msg_len = len(message) * 4
    data = struct.pack(
        "BB%ds" % (unicode_msg_len,),
        ACSPMessage.ACSP_BROADCAST_CHAT,
        len(message),
        message.encode("utf-32"),
    )
    return data


def send_message(car_id: int, message: str) -> bytes:
    if len(message) > 255:
        message = message[:225]

    unicode_len = len(message) * 4
    data = struct.pack(
        "BBB%ds" % (unicode_len,),
        ACSPMessage.ACSP_SEND_CHAT,
        car_id,
        len(message),
        message.encode("utf-32"),
    )
    return data


def car_info_request(car_id: int) -> bytes:
    return bytes([ACSPMessage.ACSP_GET_CAR_INFO, car_id])


# Incoming Messages

_ParserReturn = Tuple[_T, int]
_Parser = Callable[[bytes], _ParserReturn]


def parse_payload(payload: bytes, parsers: list[_Parser]) -> list:
    """
    Unpack a message given a UDP payload and some parsers.
    """
    data = []
    slice_ = payload

    for parser in parsers:
        parsed, inc = parser(slice_)
        data.append(parsed)
        slice_ = slice_[inc:]

    return data


def _parse_byte(chunk: bytes) -> _ParserReturn[int]:
    return struct.unpack("B", chunk[:1])[0], 1


def _parse_short(chunk: bytes) -> _ParserReturn[int]:
    return struct.unpack("H", chunk[:2])[0], 2


def _parse_int32(chunk: bytes) -> _ParserReturn[int]:
    return struct.unpack("I", chunk[:4])[0], 4


def _parse_float(chunk: bytes) -> _ParserReturn[float]:
    try:
        return struct.unpack("f", chunk[:4])[0], 4
    except struct.error:
        raise MessageParseException(f"Could not unpack to float: {chunk}")


def _parse_vector3f(chunk: bytes) -> _ParserReturn[Vector3f]:
    try:
        x = struct.unpack("f", chunk[:4])[0]
        y = struct.unpack("f", chunk[4:8])[0]
        z = struct.unpack("f", chunk[8:12])[0]
    except struct.error:
        raise MessageParseException(f"Could not unpack to Vector3f: {chunk}")

    return Vector3f(x, y, z), 12


def _parse_string(chunk: bytes) -> _ParserReturn[str]:
    strlen = chunk[0]
    string = chunk[1 : strlen + 1]

    try:
        return string.decode("utf-8"), strlen + 1
    except UnicodeDecodeError:
        raise MessageParseException(f"Could not parse as utf-8: {string}")


def _parse_unicode(chunk: bytes) -> _ParserReturn[str]:
    strlen = (
        chunk[0] * 4
    )  # first byte is the number of unicode characters (4 bytes each)
    string = chunk[1 : strlen + 1]

    try:
        return string.decode("utf-32"), strlen + 1
    except UnicodeDecodeError:
        raise MessageParseException(f"Could not parse as utf-32: {string}")


# Message Classes


class BaseMessage:
    """
    Base class for incoming messages
    Subclasses declare the class variable __parsers__, as well as type annotations for fields
    """

    __parsers__: list[_Parser]

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    @classmethod
    def from_payload(cls, message: bytes):
        data = parse_payload(message, cls.__parsers__)

        # fails if annotation order and len not consistent with parsers
        kwargs = {}
        for index, field in enumerate(cls.__annotations__):
            kwargs[field] = data[index]

        return cls(**kwargs)


class CarInfo(BaseMessage):
    __parsers__ = [
        _parse_byte,
        _parse_byte,
        _parse_unicode,
        _parse_unicode,
        _parse_unicode,
        _parse_unicode,
        _parse_unicode,
    ]

    car_id: int
    is_connected: bool
    model: str
    skin: str
    driver_name: str
    driver_team: str
    guid: str


class LapCompleted(BaseMessage):
    __parsers__ = [_parse_byte, _parse_int32, _parse_byte]

    car_id: int
    laptime: int
    cuts: int

    # TODO: leaderboard array, grip


class NewConnection(BaseMessage):
    __parsers__ = [
        _parse_unicode,
        _parse_unicode,
        _parse_byte,
        _parse_string,
        _parse_string,
    ]

    driver_name: str
    driver_guid: str
    car_id: int
    car_model: str
    car_skin: str


class NewSession(BaseMessage):
    proto_version: int
    session_index: int
    current_sess_index: int
    session_count: int
    server_name: str
    track_name: str
    track_config: str
    name: str
    session_type: int
    time: int
    laps: int
    wait_time: int
    ambient_temp: int
    track_temp: int
    weather_graph: str
    elapsed_ms: int

    __parsers__ = [
        _parse_byte,
        _parse_byte,
        _parse_byte,
        _parse_byte,
        _parse_unicode,
        _parse_string,
        _parse_string,
        _parse_string,
        _parse_byte,
        _parse_short,
        _parse_short,
        _parse_short,
        _parse_byte,
        _parse_byte,
        _parse_string,
        _parse_int32,
    ]


class ConnectionClosed(BaseMessage):
    __parsers__ = [
        _parse_unicode,
        _parse_unicode,
        _parse_byte,
        _parse_string,
        _parse_string,
    ]

    driver_name: str
    driver_guid: str
    car_id: int
    car_model: str
    car_skin: str


def parse_acsp_message(raw_message: bytes) -> BaseMessage:
    # message type (first byte)
    try:
        msg_type = ACSPMessage(raw_message[0])
    except ValueError:
        raise UnsupportedMessageException(raw_message[0])

    msg = raw_message[1:]

    try:
        return {
            ACSPMessage.ACSP_LAP_COMPLETED: LapCompleted,
            ACSPMessage.ACSP_CAR_INFO: CarInfo,
            ACSPMessage.ACSP_CONNECTION_CLOSED: ConnectionClosed,
            ACSPMessage.ACSP_NEW_CONNECTION: NewConnection,
            ACSPMessage.ACSP_NEW_SESSION: NewSession,
        }[msg_type].from_payload(msg)
    except KeyError:
        raise UnsupportedMessageException(int(msg_type))
