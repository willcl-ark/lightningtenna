import simplejson as json
import logging
import time
from pprint import pprint

from config import CONFIG

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format=CONFIG["logging"]["FORMAT"])

MSG_TYPE = {2: "BROADCAST", 3: "EMERGENCY", 1: "GROUP", 0: "PRIVATE"}


def handle_event(evt):
    return {
        "__str__": evt.__str__(),
        "event_type": evt.event_type,
        "message": evt.message,
        "status": evt.status,
        "device_details": evt.device_details,
        "disconnect_code": evt.disconnect_code,
        "disconnect_reason": evt.disconnect_reason,
        "group": evt.group,
        "device_paths": evt.device_paths,
    }


def handle_text_msg(message):
    msg = message
    payload = {
        "message": msg.message.payload.message,
        "sender": {
            "gid": msg.message.payload.sender.gid_val,
            "gid_type": msg.message.payload.sender.gid_type,
        },
        "time_sent": str(msg.message.payload.time_sent),
        "counter": msg.message.payload.counter,
        "sender_initials": msg.message.payload.sender_initials,
    }
    destination = {
        "gid_type": msg.message.destination.gid_type,
        "gid_val": msg.message.destination.gid_val,
        "type": MSG_TYPE[msg.message.destination.gid_type],
    }

    return {
        "message": {
            "destination": destination,
            "max_hops": msg.message.max_hops,
            "payload": payload,
        }
    }


def wait_for(success, timeout=20, interval=1):
    start_time = time.time()
    while not success() and time.time() < start_time + timeout:
        time.sleep(interval)
    if time.time() > start_time + timeout:
        raise ValueError("Error waiting for {}", success)


def check_connection(func):
    def exists(*args, **kwargs):
        if g.CONN is None:
            return {
                "status": "Connection does not exist. \
                    First create connection using 'sdk_token()'"
            }
        result = func(*args, **kwargs)
        return result

    return exists


def cli(func):
    def if_cli(*args, **kwargs):
        result = func(*args, **kwargs)
        if args[0].cli:
            if result is not None:
                pprint(result)
        return result

    return if_cli


def segment(msg, segment_size: int):
    """
    :param msg: string or json-compatible object
    :param segment_size: integer
    :return: list of strings ready for sequential transmission
    """

    try:
        if not isinstance(msg, str):
            msg = json.dumps(msg)
    except Exception as e:
        logger.debug(e)
        return
    prefix = "sm"
    msg_length = len(msg)
    if msg_length % segment_size == 0:
        num_segments = int(msg_length / segment_size)
    else:
        num_segments = int((msg_length // segment_size) + 1)

    msg_list = []
    for i in range(0, msg_length, segment_size):
        header = f"{prefix}/{(i // segment_size) + 1}/{num_segments}/"
        msg_list.append(header + msg[i: i + segment_size])
    return msg_list


def de_segment(segment_list: list):
    """
    :param segment_list: a list of prefixed strings
    :return: prefix-removed, concatenated string
    """
    # remove erroneous segments
    for i in segment_list:
        if not i.startswith("sm/"):
            del segment_list[i]
    segment_list.sort()

    # remove the header and compile result
    result = ""
    for i in segment_list:
        a, b, c, msg = i.split("/")
        result += msg
    return result


def log(message, cli):
    if cli:
        print(message)
    else:
        logger.debug(message)
