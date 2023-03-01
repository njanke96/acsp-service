"""
ACSP Exceptions
"""


class UnsupportedMessageException(Exception):
    def __init__(self, message_id: int):
        super().__init__(f"Unsupported message ID: {message_id}")


class MessageParseException(Exception):
    pass
