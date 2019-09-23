import queue
import select
import socket
import threading

from config import CONFIG
from gotenna_connections import setup_gotenna_conn
from utilities import hexdump, naturalsize, mesh_auto_send


gateway_conn = setup_gotenna_conn(name="GATEWAY", gateway=1)

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
remote_socket.connect(
    (
        CONFIG["lightning"]["REMOTE_PEER_IP"],
        int(CONFIG["lightning"]["REMOTE_PEER_PORT"]),
    )
)
inputs.append(remote_socket)
outputs.append(remote_socket)
message_queues[remote_socket] = gateway_conn.events.send_via_socket


# main select loop
try:
    while inputs:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        for s in readable:
            data = s.recv(int(CONFIG["lightning"]["RECV_SIZE"]))
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
