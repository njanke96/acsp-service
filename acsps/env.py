import os

ACSPS_SQLITE_PATH = os.environ.get("ACSPS_SQLITE_PATH", "/tmp/acsps.db")
ACSPS_UDP_ADDR = os.environ.get("ACSPS_UDP_ADDR", "127.0.0.1")
ACSPS_UDP_PORT = os.environ.get("ACSPS_UDP_PORT", "11200")
ACSPS_WEB_ADDR = os.environ.get("ACSPS_WEB_ADDR", "0.0.0.0")
ACSPS_WEB_PORT = os.environ.get("ACSPS_WEB_PORT", "8000")

