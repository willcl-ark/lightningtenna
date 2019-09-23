import queue
import select
import socket
import threading
import time
from config import CONFIG
from connection import Connection

from utilities import hexdump, naturalsize

LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 9733
REMOTE_IP = "77.98.116.8"
REMOTE_PORT = 9733
RECV_SIZE = 210

# setup goTenna mesh connections
mesh_conn = Connection(name="MESH")
mesh_conn.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
mesh_conn.set_gid(int(CONFIG["gotenna"]["DEBUG_GID"]))
mesh_conn.set_geo_region(int(CONFIG["gotenna"]["GEO_REGION"]))

gateway_conn = Connection(name="GATEWAY")
gateway_conn.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
gateway_conn.set_gid(int(CONFIG["gotenna"]["GID"]))
gateway_conn.set_geo_region(int(CONFIG["gotenna"]["GEO_REGION"]))


def mesh_auto_send(conn, name):
    """Auto sends messages from the queue via mesh link
    """
    while True:
        if not conn.events.send_via_mesh.empty():
            data = conn.events.send_via_mesh.get()
            conn.send_broadcast(data, binary=True)
            conn.log(
                f"Message sent! {name} send_via_mesh queue now contains {conn.events.send_via_mesh.qsize()} buffered messages"
            )

        else:
            time.sleep(0.5)


# threads which will run auto-send
mesh_send_thread = threading.Thread(target=mesh_auto_send, args=[mesh_conn, "MESH"])
mesh_send_thread.start()
gateway_send_thread = threading.Thread(
    target=mesh_auto_send, args=[gateway_conn, "GATEWAY"]
)
gateway_send_thread.start()

# inputs, outputs and queues for select
inputs = []
outputs = []
message_queues = {}

# Server setup -- will accept a single connection "local" and add it to select
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(False)
server.bind((LOCAL_IP, LOCAL_PORT))
server.listen(5)
# hack to force waiting for local C-Lightning connection
mesh_socket = None
while True:
    try:
        mesh_socket, client_address = server.accept()
        mesh_socket.setblocking(False)
        inputs.append(mesh_socket)
        outputs.append(mesh_socket)
        message_queues[mesh_socket] = mesh_conn.events.send_via_socket
        break
    except BlockingIOError:
        time.sleep(1)
        pass

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
                if s is mesh_socket:
                    mesh_conn.events.send_via_mesh.put(data)
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
