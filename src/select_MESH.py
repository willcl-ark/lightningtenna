import queue
import select
import socket
import threading
import time
from config import CONFIG
from connection import Connection

from utilities import hexdump, naturalsize, mesh_auto_send

LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 9733
RECV_SIZE = 210

# setup goTenna mesh connections
mesh_conn = Connection(name="MESH")
mesh_conn.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
mesh_conn.set_gid(int(CONFIG["gotenna"]["DEBUG_GID"]))
mesh_conn.set_geo_region(int(CONFIG["gotenna"]["GEO_REGION"]))


# threads which will run auto-send
mesh_send_thread = threading.Thread(target=mesh_auto_send, args=[mesh_conn, "MESH"])
mesh_send_thread.start()

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
