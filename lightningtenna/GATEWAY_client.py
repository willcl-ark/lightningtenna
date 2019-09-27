import threading
import time

from gotenna_connections import setup_gotenna_conn
from trio_sockets import TrioSocket
from utilities import mesh_auto_send


# setup goTenna gateway connection
gateway_connection = setup_gotenna_conn(name="GATEWAY|MESH", offgrid=0)


# start a mesh send thread
mesh_send_thread = threading.Thread(
    target=mesh_auto_send,
    args=[gateway_connection.send_broadcast, gateway_connection.events.send_via_mesh],
)
mesh_send_thread.start()
while not mesh_send_thread.is_alive():
    time.sleep(0.1)


# start the outbound connection
socket = TrioSocket(
    gateway_connection.events.send_via_socket,
    gateway_connection.events.send_via_mesh,
    "GATEWAY",
)
socket_thread = threading.Thread(target=socket.start_client, daemon=True)
socket_thread.start()


# temporary main loop
try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    ...
