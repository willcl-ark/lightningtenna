import os
from configparser import RawConfigParser
from shutil import copyfile


home = os.path.expanduser("~")
config_path = home + "/.lightningtenna/"


DEFAULT_CONFIG_FILE = config_path + "config.ini"
SEND_TIMES = []


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
