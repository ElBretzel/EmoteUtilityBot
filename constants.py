import sys
import os

import pytz

PREFIX = ","
OS_SLASH = "\\" if sys.platform == "win32" else "/"
DIRECTORY = os.path.abspath(os.path.dirname(__file__))
KEY_DIRECTORY = f"{DIRECTORY}{OS_SLASH}keys{OS_SLASH}"
EVENTS_DIRECTORY = f"{DIRECTORY}{OS_SLASH}events{OS_SLASH}"
COGS_DIRECTORY = f"{DIRECTORY}{OS_SLASH}cogs{OS_SLASH}"
LOGS_DIRECTORY = f"{DIRECTORY}{OS_SLASH}logs{OS_SLASH}"
TIMEZONE = pytz.timezone('Europe/Paris')
DEV = 232920242110726144
MAX_SIZE = 800