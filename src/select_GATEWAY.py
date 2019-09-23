import queue
import select
import socket
import threading
import time
from config import CONFIG
from connection import Connection

from utilities import hexdump, naturalsize, mesh_auto_send

REMOTE_IP = "77.98.116.8"
REMOTE_PORT = 9733
RECV_SIZE = 210

# setup goTenna mesh connections
gateway_conn = Connection(name="GATEWAY")
gateway_conn.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
gateway_conn.set_gid(int(CONFIG["gotenna"]["GID"]))
gateway_conn.set_geo_region(int(CONFIG["gotenna"]["GEO_REGION"]))


# thread which will run auto-send
gateway_send_thread = threading.Thread(
    target=mesh_auto_send, args=[gateway_conn, "GATEWAY"]
)
gateway_send_thread.start()

# inputs, outputs and queues for select
inputs = []
outputs = []
message_queues = {}

#
# remote setup -- will create an outbound socket to remote C-Lightning node and add it
# to select
remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
remote_socket.connect((REMOTE_IP, REMOTE_PORT))
inputs.append(remote_socket)
outputs.append(remote_socket)
message_queues[remote_socket] = gateway_conn.events.send_via_socket


# main select loop
try:
    while inputs:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        for s in readable:
            data = s.recv(RECV_SIZE)
            if data:
                print(f"\nRead {naturalsize(len(data))} data from {s.getsockname()}:")
                hexdump(data)
                if s is remote_socket:
                    gateway_conn.events.send_via_mesh.put(data)
            else:
                s.close()
                print(f"SOCKET CLOSED: {s.getsockname()}")

        for s in writable:
            try:
                next_msg = message_queues[s].get_nowait()
            except queue.Empty:
                pass
                # outputs.remove(s)
            else:
                print(
                    f"Sending {naturalsize(len(next_msg))} data to {s.getsockname()}\n"
                )
                s.send(next_msg)

        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()
            del message_queues[s]
except KeyboardInterrupt:
    for s in outputs:
        s.close()
