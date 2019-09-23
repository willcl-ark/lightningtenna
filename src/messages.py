import base58
import threading
import types
from time import sleep, time

from goTenna.payload import BinaryPayload
from utilities import de_segment, naturalsize, hexdump

RHOST = "77.98.116.8"
RPORT = 9733
MAGIC = b"clight"


def valid_base58check(data):
    try:
        base58.b58decode_check(data)
        print("Base58 encoded data detected")
        return True
    except Exception:
        return False


def handle_message(conn, message):
    """
    Handle messages received over the mesh network
    :param conn: the lntenna.gotenna.Connection instance
    :param message: as strings
    :return: result of message handling
    """
    if isinstance(message.payload, BinaryPayload):
        payload = message.payload._binary_data
        conn.log(f"Received binary payload:\n{hexdump(payload)}")
        # stick binary messages right onto the socket queue
        conn.events.send_via_socket.put(payload)
        conn.log("Added payload to send_via_socket queue!")
    else:
        payload = message.payload.message
        # test for jumbo:
        jumbo = True if payload.startswith("sm/") else False
        if jumbo:
            handle_jumbo_message(conn, message)
            return
        if valid_base58check(payload):
            conn.bytes_received += len(payload)
            conn.log(f"Total bytes received: {naturalsize(conn.bytes_received)}")
            try:
                payload_bytes = base58.b58decode_check(payload)
                if payload_bytes.startswith(MAGIC):
                    print("magic message received!")
                    original_payload = payload_bytes[6:]
                    conn.events.send_via_socket.put(original_payload)
                print(payload_bytes[:6])
            except Exception as e:
                print(f"Error decoding data in handle_message:\n{e}")
        else:
            print(payload)


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
