import threading
import types
from collections import namedtuple
from time import sleep, time

from goTenna.payload import BinaryPayload, CustomPayload
from termcolor import cprint

from config import VALID_MSGS
from utilities import de_segment, naturalsize, hexdump


def handle_message(conn, message):
    """
    Handle messages received over the mesh network
    :param conn: the lntenna.gotenna.Connection instance
    :param message: as strings
    :return: result of message handling
    """
    if isinstance(message.payload, CustomPayload):
        print(message)
    elif isinstance(message.payload, BinaryPayload):
        payload = message.payload._binary_data
        conn.bytes_received += len(payload)
        cprint(f"Received {naturalsize(len(payload))}", "cyan")
        # hexdump(payload, recv=True)
        if not payload[0:4] in VALID_MSGS:
            print("Message magic not found in VALID_MSGS. Discarding message")
            return
        conn.events.send_via_socket.put(payload[4:])
    else:
        payload = message.payload.message
        # test for jumbo:
        jumbo = True if payload.startswith("sm/") else False
        if jumbo:
            handle_jumbo_message(conn, message)
            return
        else:
            print(payload)


def handle_jumbo_message(conn, message):
    """Handle a jumbo message received.
    """
    payload = message.payload.message
    # TODO: this cuts out all sender and receiver info -- ADD SENDER GID
    conn.log(f"Received jumbo message fragment")
    prefix, seq, length, msg = payload.split("/")

    # if a jumbo monitor thread is not running, start one
    if conn.jumbo_thread.is_alive():
        pass
    else:
        conn.events.jumbo_len = length
        conn.jumbo_thread = None
        conn.jumbo_thread = threading.Thread(
            target=monitor_jumbo_msgs, daemon=True, args=[conn]
        )
        conn.jumbo_thread.start()
    # add the message to the events.jumbo queue
    conn.events.jumbo.append(payload)
    return


def monitor_jumbo_msgs(conn, timeout=210):
    conn.log("Starting jumbo message monitor thread")
    start = time()
    missing = True
    while True and time() < start + timeout:
        # conn.log(
        #     f"received: {len(conn.events.jumbo)} of {conn.events.jumbo_len} "
        #     f"jumbo messages"
        # )
        if (
            len(conn.events.jumbo) == int(conn.events.jumbo_len)
            and len(conn.events.jumbo) is not 0
        ):
            missing = False
            # give handle_message the attributes it expects
            jumbo_message = types.SimpleNamespace()
            jumbo_message.payload = types.SimpleNamespace()
            # reconstruct the jumbo message
            jumbo_message.payload.message = de_segment(conn.events.jumbo)
            # send it back through handle_message
            conn.log(f"Jumbo message payload reconstituted")
            handle_message(conn, jumbo_message)
            break
        sleep(0.2)
    # reset jumbo events after timeout
    conn.events.init_jumbo()
    if missing:
        conn.log(
            "Did not receive all jumbo messages require for re-assembly. "
            "Please request the message again from the remote host."
        )
    return


"""
Message Structure:

Size    | Description
-----------------------
4       | Magic / Protocol
16      | Host
2       | Port
4       | Checksum / Peer (ID)

This will associate this checksum (peer) with this ip address/port configuration, for
this protocol.

Future messages must all be prefixed with `Checksum`.

Messages not prefixed with a valid Magic or Checksum will be discarded.
"""


# checksums = {}
# Peer = namedtuple("Peer", ["host", "port", "protocol"])
#
#
# def handle_binary_msg(msg):
#     # throw away the message if it's not in magic or the checksum DB
#     prefix = msg[0:4]
#     if prefix not in MAGIC and checksums:
#         print(f"Message prefix unknown: {msg[0:4]}")
#         return
#
#     if prefix in MAGIC:
#         if not len(msg) == 26:
#             print(f"Invalid message length for magic negotiation: {len(msg)}")
#             return
#         # add the host, port, protocol to the peer's entry in checksums
#         checksums[prefix] = Peer(msg[4:20], msg[20:22], msg[0:4])
#         print(f"Peer {prefix} added to in-memory peer dictionary")
#
#     elif prefix in checksums:
#         # if ltng protocol, just strip the header and return it for now
#         if checksums[prefix] == b"ltng":
#             print(f"Peer {prefix}'s message stripped and returned")
#             return msg[4:]
