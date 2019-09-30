import threading
import types
from time import sleep, time

from goTenna.payload import BinaryPayload

from utilities import de_segment, naturalsize, hexdump


def handle_message(conn, message):
    """
    Handle messages received over the mesh network
    :param conn: the lntenna.gotenna.Connection instance
    :param message: as strings
    :return: result of message handling
    """
    if isinstance(message.payload, BinaryPayload):
        payload = message.payload._binary_data
        conn.events.send_via_socket.put(payload)
        conn.bytes_received += len(payload)
        conn.log(f"Received {naturalsize(len(payload))} -- "
                 f"Total: {naturalsize(conn.bytes_received)}")
        hexdump(payload)
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
