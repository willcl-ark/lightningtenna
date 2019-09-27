import threading
import time

import trio

from gotenna_connections import setup_gotenna_conn
from trio_sockets import TrioSocket
from utilities import mesh_auto_send


# setup a goTenna mesh connection
mesh_connection = setup_gotenna_conn(name="MESH|MESH", offgrid=1)


# start a thread to send messages it finds in it's queue, over the mesh
mesh_send_thread = threading.Thread(
    target=mesh_auto_send,
    args=[mesh_connection.send_broadcast, mesh_connection.events.send_via_mesh],
)
mesh_send_thread.start()
while not mesh_send_thread.is_alive():
    time.sleep(0.1)


# start the listening server. MESH's C-Lightning instance will connect to this!
socket = TrioSocket(
    mesh_connection.events.send_via_socket, mesh_connection.events.send_via_mesh, "MESH"
)
socket_thread = threading.Thread(
    target=trio.run, args=[socket.start_server], daemon=True
)
socket_thread.start()


# temporary main loop
try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    ...
