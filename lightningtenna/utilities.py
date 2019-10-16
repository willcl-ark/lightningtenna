import functools
import ipaddress
import logging
import time
from pprint import pprint

import simplejson as json
import trio
from termcolor import colored

import config

logger = logging.getLogger("UTIL")
mesh_logger = logging.getLogger("MESH")


SERVER_PORT = config.CONFIG["lightning"]["SERVER_PORT"]
MSG_TYPE = {2: "BROADCAST", 3: "EMERGENCY", 1: "GROUP", 0: "PRIVATE"}


def hexdump(data, recv=None, send=None, length=16):
    """Print a hexdump of data
    """
    filter = "".join([(len(repr(chr(x))) == 3) and chr(x) or "." for x in range(256)])
    lines = []
    digits = 4 if isinstance(data, str) else 2
    for c in range(0, len(data), length):
        chars = data[c : c + length]
        hex = " ".join(["%0*x" % (digits, (x)) for x in chars])
        printable = "".join(
            ["%s" % (((x) <= 127 and filter[(x)]) or ".") for x in chars]
        )
        lines.append("%04x  %-*s  %s\n" % (c, length * 3, hex, printable))
    result = "\n" + "".join(lines)
    if recv:
        mesh_logger.debug(colored(result, "cyan"))
    elif send:
        mesh_logger.debug(colored(result, "magenta"))
    else:
        logger.debug(result)


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


def cli(func):
    """If we are running a cli program, try to pprint stuff
    """

    def if_cli(*args, **kwargs):
        result = func(*args, **kwargs)
        if args[0].cli:
            if result is not None:
                pprint(result)
        return result

    return if_cli


def print_timer(length, interval=1):
    """Will print a pretty timer to the console while we wait for something to complete
    """
    mesh_logger.info(f"Waiting {length} seconds due to bandwidth restrictions")

    for remaining in range(length, 0, interval * -1):
        if remaining % 10 == 0:
            mesh_logger.info(f"{remaining} seconds remaining")
        time.sleep(1)


def rate_dec(private=False):

    def rate_limit(func):
        """Smart rate-limiter
        """

        @functools.wraps(func)
        def limit(*args, **kwargs):
            # how many can we send per minute
            if not config.UBER:
                per_min = 5
            else:
                per_min = 5 if not private else 999
            min_interval = 0.5

            # add this send time to the list
            config.SEND_TIMES.append(time.time())

            # if we've not sent before, send!
            if len(config.SEND_TIMES) <= 1:
                pass

            # if we've not sent 'per_min' in total, sleep & send!
            elif len(config.SEND_TIMES) < per_min + 1:
                time.sleep(min_interval)
                pass

            # if our 'per_min'-th oldest is older than 'per_min' secs ago, go!
            elif config.SEND_TIMES[-(per_min + 1)] < (time.time() - 60):
                time.sleep(min_interval)
                pass

            # wait the required time
            else:
                wait = int(60 - (time.time() - config.SEND_TIMES[-(per_min + 1)])) + 1
                print_timer(wait)

            # execute the send
            return func(*args, **kwargs)

        return limit

    return rate_limit


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
        logger.error(e)
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
        msg_list.append(header + msg[i : i + segment_size])
    return msg_list


def sort_segment(val):
    a, b, c, msg = val.split("/")
    return int(b)


def de_segment(segment_list: list):
    """
    :param segment_list: a list of prefixed strings
    :return: prefix-removed, concatenated string
    """
    # remove erroneous segments
    for i in segment_list:
        if not i.startswith("sm/"):
            del segment_list[i]
    segment_list.sort(key=sort_segment)

    # remove the header and compile result
    result = ""
    for i in segment_list:
        a, b, c, msg = i.split("/")
        result += msg
    return result


suffixes = {
    "decimal": ("kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"),
    "binary": ("KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"),
    "gnu": "KMGTPEZY",
}


def naturalsize(value, binary=False, gnu=True, format="%.1f"):
    """show us sizes nicely formatted
    https://github.com/jmoiron/humanize.git
    """
    if gnu:
        suffix = suffixes["gnu"]
    elif binary:
        suffix = suffixes["binary"]
    else:
        suffix = suffixes["decimal"]

    base = 1024 if (gnu or binary) else 1000
    bytes = float(value)

    if bytes == 1 and not gnu:
        return "1 Byte"
    elif bytes < base and not gnu:
        return "%d Bytes" % bytes
    elif bytes < base and gnu:
        return "%dB" % bytes

    for i, s in enumerate(suffix):
        unit = base ** (i + 2)
        if bytes < unit and not gnu:
            return (format + " %s") % ((base * bytes / unit), s)
        elif bytes < unit and gnu:
            return (format + "%s") % ((base * bytes / unit), s)
    if gnu:
        return (format + "%s") % ((base * bytes / unit), s)
    return (format + " %s") % ((base * bytes / unit), s)


async def mesh_auto_send(args):
    """Asynchronously sends messages from the queue via mesh link
    """
    send_method, mesh_queue, gid = args
    while True:
        async for data in mesh_queue:
            send_method(gid=gid, message=data, binary=True)


async def mesh_to_socket_queue(args):
    """Hack to move messages from mesh_recv queue and send them back to the socket
    """
    mesh_queue, socket_queue = args
    while True:
        if mesh_queue.empty():
            await trio.sleep(0.5)
        else:
            await socket_queue.send(mesh_queue.get())


def print_list(my_list):
    """Print a nicely formatted enumerated list
    """
    for c, v in enumerate(my_list):
        print(c, v)


async def chunk_to_list(data, chunk_len):
    """Adds data of arbitrary length to a queue in a certain chunk size
    """
    for i in range(0, len(data), chunk_len):
        yield (b"ltng" + data[i : i + chunk_len])


def get_id_addr_port():
    """Ask the user for peer, IP address and port to modify as gateway
    """
    to_modify = input("Enter 'id' (number) of the gateway ('c' to cancel/skip): ")
    if to_modify == "c":
        return
    while True:
        address = (
            input("What ip address should we assign them? (default: 127.0.0.1): ")
            or "127.0.0.1"
        )
        try:
            ipaddress.ip_address(address)
            break
        except ValueError:
            logger.exception(f"Not a valid ip address. Please try again")

    while True:
        try:
            port = (
                input(
                    f"What port should we assign them? "
                    f"(default from config: {SERVER_PORT}): "
                )
                or SERVER_PORT
            )
            if not port.isdigit():
                raise TypeError
            if 1 <= int(port) <= 65535:
                break
            else:
                raise ValueError
        except (ValueError, TypeError):
            logger.exception(
                f"{port} is not a valid port number. Must be between 1 and 65535.\n"
            )

    return to_modify, address, port
