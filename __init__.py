import logging
import logging.handlers
import os

import toml

CONF_PATH = "config.toml"
config = toml.load(CONF_PATH)

DEBUG = True
if not os.environ.get("DEBUG"):
    DEBUG = False
    os.environ.setdefault("FLASK_ENV", "production")

logging.TRACE = 5
logging.addLevelName(logging.TRACE, "trace")
logging.trace = lambda *args, **kwargs: logging.log(5, *args, **kwargs)
LOG_FILE = "cowin_booking.log"

stderr_handler = logging.StreamHandler()
file_handler = logging.FileHandler(LOG_FILE, mode="a")
logging.basicConfig(
    handlers=[stderr_handler, file_handler],
    level=logging.TRACE if DEBUG else logging.DEBUG,  # more verbose if debugging
    format="{asctime} - {levelname} - {message}",
    style="{",
)
