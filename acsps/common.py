"""
Common
"""


def format_ms_time(millis: int) -> str:
    minutes, millis = divmod(millis, 60000)
    seconds, millis = divmod(millis, 1000)

    time_string = f"{minutes:02}:{seconds:02}.{millis:03}"
    return time_string
