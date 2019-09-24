import queue
import select
import socket
from hashlib import sha256

from config import CONFIG
from gotenna_connections import setup_gotenna_conn
from utilities import hexdump, naturalsize, print_list


mesh_conn = setup_gotenna_conn(name="MESH")

# inputs, outputs and queues for select
inputs = []
outputs = []
message_queues = {}
sent_messages = {}
received_messages = {}

# Server setup -- listening socket will accept new connections and add them to select
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(False)
server.bind(
        (
            CONFIG["lightning"]["LOCAL_SERVER_IP"],
            int(CONFIG["lightning"]["LOCAL_SERVER_PORT"])
        )
)
server.listen(5)
inputs.append(server)


# main select loop
try:
    while inputs:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        for s in readable:
            if s is server:
                # only works for a single Lightning conn!
                mesh_socket, client_address = s.accept()
                mesh_socket.setblocking(0)
                inputs.append(mesh_socket)
                message_queues[mesh_socket] = mesh_conn.events.send_via_socket
                sent_messages[mesh_socket] = []
                received_messages[mesh_socket] = []
            else:
                data = s.recv(int(CONFIG["lightning"]["RECV_SIZE"]))
                if data:
                    print(f"\nRead {naturalsize(len(data))} data from {s.getsockname()}, {s.fileno()}:")
                    # hexdump(data)
                    mesh_conn.events.send_via_mesh.put(data)
                    received_messages[s].append(sha256(data).hexdigest())
                    print(f"Messages received on {s.getsockname()}:\n"
                          f"{print_list(received_messages[s])}")
                else:
                    print(f"CLOSING SOCKET: {s.getsockname()}")
                    s.close()
                    inputs.remove(s)
                    outputs.remove(s)
                if s not in outputs:
                    outputs.append(s)

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
