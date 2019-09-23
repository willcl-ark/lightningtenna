import queue
import select
import socket
import time

from config import CONFIG
from gotenna_connections import setup_gotenna_conn
from utilities import hexdump, naturalsize


mesh_conn = setup_gotenna_conn(name="MESH")

# inputs, outputs and queues for select
inputs = []
outputs = []
message_queues = {}

# Server setup -- will accept a single connection "local" and add it to select
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(False)
server.bind(
        (
            CONFIG["lightning"]["LOCAL_SERVER_IP"],
            int(CONFIG["lightning"]["LOCAL_SERVER_PORT"])
        )
)
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
            data = s.recv(int(CONFIG["lightning"]["RECV_SIZE"]))
            if data:
                print(f"\nRead {naturalsize(len(data))} data from {s.getsockname()}:")
                hexdump(data)
                if s is mesh_socket:
                    mesh_conn.events.send_via_mesh.put(data)
            else:
                print(f"CLOSING SOCKET: {s.getsockname()}")
                s.close()

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
