import os
from configparser import RawConfigParser
from shutil import copyfile

# get user home directory based on OS
home = os.path.expanduser("~")
config_path = home + "/.lightningtenna/"


DEFAULT_CONFIG_FILE = config_path + "config.ini"


def get_config_file():
    """Returns a config file path. Copies example_config.ini over into default path if
    not located
    """
    if not os.path.exists(config_path):
        print(f"Config file not found, copying example config... to {config_path}")
        os.makedirs(config_path)
    if not os.path.exists(config_path + "config.ini"):
        example_config = os.path.join(os.path.dirname(__file__), "example_config.ini")
        copyfile(example_config, config_path + "config.ini")
    return os.environ.get("CONFIG_FILE", DEFAULT_CONFIG_FILE)


CONFIG_FILE = get_config_file()


def create_config(config_file=None):
    """Creates the config dict
    """
    parser = RawConfigParser()
    parser.read(config_file or CONFIG_FILE)
    return parser


CONFIG = create_config()
