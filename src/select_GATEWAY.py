import select
import socket
import queue
import time
import threading

from utilities import hexdump, print_timer, naturalsize


LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 9733
REMOTE_IP = "77.98.116.8"
REMOTE_PORT = 9733
RECV_SIZE = 210

ART_DELAY = 13


import time
from config import CONFIG
from connection import Connection


c = Connection(server=0)
c.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
c.set_gid(int(CONFIG["gotenna"]["GID"]))
c.set_geo_region(int(CONFIG["gotenna"]["GEO_REGION"]))


def mesh_auto_send(conn):
    while True:
        if not conn.events.send_via_mesh.empty():
            data = conn.events.send_via_mesh.get()
            conn.send_broadcast(data, binary=True)
        else:
            time.sleep(0.5)


mesh_send_thread = threading.Thread(target=mesh_auto_send, args=[c])
mesh_send_thread.start()


inputs = []
outputs = []
message_queues = {}

# # Server setup -- will accept new connection "local" and add it to select
# server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# server.setblocking(False)
# server.bind((LOCAL_IP, LOCAL_PORT))
# server.listen(5)
# # hack to force waiting for local C-Lightning connection
# local = None
# while True:
#     try:
#         local, client_address = server.accept()
#         local.setblocking(False)
#         inputs.append(local)
#         outputs.append(local)
#         message_queues[local] = c.events.send_via_socket
#         break
#     except BlockingIOError:
#         time.sleep(1)
#         pass


# remote setup -- will create an outbound socket
remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
remote.connect((REMOTE_IP, REMOTE_PORT))
inputs.append(remote)
outputs.append(remote)
message_queues[remote] = c.events.send_via_socket


while inputs:
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
    for s in readable:
        data = s.recv(RECV_SIZE)
        if data:
            print(f"\nRead {naturalsize(len(data))} data from {s.getsockname()}:")
            hexdump(data)
            if s is remote:
                # add received C-Lightning socket msgs to mesh queue
                c.events.send_via_mesh.put(data)
        else:
            # don't close the socket!
            pass

    for s in writable:
        try:
            next_msg = message_queues[s].get_nowait()
        except queue.Empty:
            pass
            # outputs.remove(s)
        else:
            print(f"Sending {naturalsize(len(next_msg))} data to {s.getsockname()}\n")
            s.send(next_msg)

    for s in exceptional:
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()
        del message_queues[s]