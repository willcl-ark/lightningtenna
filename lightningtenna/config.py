import logging
import logging.handlers
import os
from configparser import RawConfigParser
from shutil import copyfile


home = os.path.expanduser("~")
config_path = home + "/.lightningtenna/"


DEFAULT_CONFIG_FILE = config_path + "config.ini"
SEND_TIMES = []

# logging
LOG_FILENAME = f"{config_path}lightningtenna.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)-15s %(levelname)-8s %(message)s",
    datefmt="%m-%d %H:%M",
    filename=LOG_FILENAME,
    filemode="w",
)
# define a Handler which writes INFO messages or higher to the sys.stderr
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter("%(name)-6s: %(levelname)-8s %(message)s")
# tell the console handler to use this format
ch.setFormatter(formatter)
# enable log file rotation
rh = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=500000, backupCount=2)
# add the console and file handlers to the root logger
logging.getLogger("").addHandler(ch)
logging.getLogger("").addHandler(rh)
logging.getLogger("goTenna").setLevel(logging.CRITICAL)


def debug_logging():
    logging.getLogger("").removeHandler(ch)
    ch2 = logging.StreamHandler()
    ch2.setLevel(logging.DEBUG)
    ch2.setFormatter(formatter)
    logging.getLogger("").addHandler(ch2)
    logging.getLogger("goTenna").setLevel(logging.DEBUG)


# config file handling
def get_config_file():
    if not os.path.exists(config_path):
        print(f"Config file not found, copying example config... to {config_path}")
        os.makedirs(config_path)
    if not os.path.exists(config_path + "config.ini"):
        example_config = os.path.join(os.path.dirname(__file__), "example_config.ini")
        copyfile(example_config, config_path + "config.ini")
    return os.environ.get("CONFIG_FILE", DEFAULT_CONFIG_FILE)


CONFIG_FILE = get_config_file()


def create_config(config_file=None):
    parser = RawConfigParser()
    parser.read(config_file or CONFIG_FILE)
    return parser


CONFIG = create_config()

# an in-memory, ephemeral list of message magic we will accept
VALID_MSGS = [b"ltng", b"http"]
