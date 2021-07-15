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

file_handler = logging.FileHandler(LOG_FILE, mode="a")
handlers: list[logging.Handler] = [file_handler]
if DEBUG:
    stderr_handler = logging.StreamHandler()
    handlers.append(stderr_handler)
logging.basicConfig(
    handlers=handlers,
    level=logging.TRACE if DEBUG else logging.DEBUG,  # more verbose if debugging
    format="{asctime} - {levelname} - {message}",
    style="{",
)
