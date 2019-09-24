import queue
import select
import socket
from hashlib import sha256

from config import CONFIG
from gotenna_connections import setup_gotenna_conn
from utilities import hexdump, naturalsize, print_list


gateway_conn = setup_gotenna_conn(name="GATEWAY", gateway=1)

# inputs, outputs and queues for select
inputs = []
outputs = []
message_queues = {}
sent_messages = {}
received_messages = {}

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
sent_messages[remote_socket] = []
received_messages[remote_socket] =[]


# main select loop
try:
    while inputs:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        for s in readable:
            data = s.recv(int(CONFIG["lightning"]["RECV_SIZE"]))
            if data:
                print(f"\nRead {naturalsize(len(data))} data from {s.getsockname()}:")
                # hexdump(data)
                if s is remote_socket:
                    gateway_conn.events.send_via_mesh.put(data)
                    received_messages[s].append(sha256(data).hexdigest())
                    print(f"Messages received on {s.getsockname()}:\n"
                          f"{print_list(received_messages[s])}")
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
                sent_messages[s].append(sha256(next_msg).hexdigest())
                print(f"Messages sent on {s.getsockname()}:\n"
                      f"{print_list(sent_messages[s])}")

        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()
            del message_queues[s]
except KeyboardInterrupt:
    for s in outputs:
        s.close()
