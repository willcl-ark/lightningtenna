import base58
import pickle
import threading
import types
from time import sleep, time

from utilities import de_segment


def handle_message(conn, message):
    """
    Handle messages received over the mesh network
    :param conn: the lntenna.gotenna.Connection instance
    :param message: as strings
    :return: result of message handling
    """
    payload = message.payload.message

    # test for jumbo:
    jumbo = True if payload.startswith("sm/") else False
    if jumbo:
        handle_jumbo_message(conn, message)
        return
    elif payload.startswith("b'"):
        payload = payload[2:]
        payload = payload[:-1]
        p = payload.encode()
        p58 = base58.b58decode(p)
        ppickle = pickle.loads(p58)
        print(f"Received a {type(ppickle)} message:")
        print(ppickle)
    else:
        print(payload)

    # handle


def handle_jumbo_message(conn, message):
    payload = message.payload.message
    # TODO: this cuts out all sender and receiver info -- ADD SENDER GID
    conn.log(f"Received jumbo message fragment")
    prefix, seq, length, msg = payload.split("/")
    if conn.jumbo_thread.is_alive():
        pass
    else:
        # start the jumbo monitor thread
        conn.events.jumbo_len = length
        conn.jumbo_thread = None
        conn.jumbo_thread = threading.Thread(
            target=monitor_jumbo_msgs, daemon=True, args=[conn]
        )
        conn.jumbo_thread.start()
    conn.events.jumbo.append(payload)
    return


def monitor_jumbo_msgs(conn, timeout=30):
    conn.log("Starting jumbo message monitor thread")
    start = time()
    missing = True
    while True and time() < start + timeout:
        conn.log(
            f"received: {len(conn.events.jumbo)} of {conn.events.jumbo_len} "
            f"jumbo messages"
        )
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
        sleep(5)
    # reset jumbo events after timeout
    conn.events.init_jumbo()
    if missing:
        conn.log(
            "Did not receive all jumbo messages require for re-assembly. "
            "Please request the message again from the remote host."
        )
    return
