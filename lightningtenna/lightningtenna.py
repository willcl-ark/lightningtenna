"""Lightningtenna.py

Usage:
  lightningtenna.py (-g | --gateway)
  lightningtenna.py (-m | --mesh)
  lightningtenna.py (-h | --help)

Options:
  -h --help        Show this screen.
  -g --gateway     Start a gateway node
  -m --mesh        Start a mesh node server

"""
import threading
import time

import trio
from docopt import docopt

from gotenna_connections import setup_gotenna_conn
from trio_sockets import TrioSocket
from utilities import mesh_auto_send


class LightningTenna:
    def __init__(self, name, offgrid):
        # setup a goTenna mesh connection
        self.mesh_connection = setup_gotenna_conn(name=f"{name}|MESH", offgrid=offgrid)
        self.start_mesh_thread()
        if offgrid:
            self.start_server()
        else:
            self.start_connection()
        print("Lightningtenna node started!")

    def start_mesh_thread(self):
        # start a thread to send messages it finds in it's queue, over the mesh
        mesh_send_thread = threading.Thread(
            target=mesh_auto_send,
            args=[
                self.mesh_connection.send_broadcast,
                self.mesh_connection.events.send_via_mesh,
            ],
        )
        mesh_send_thread.start()
        while not mesh_send_thread.is_alive():
            time.sleep(0.1)

    def start_server(self):
        # start the listening server. MESH's C-Lightning instance will connect to this!
        socket = TrioSocket(
            self.mesh_connection.events.send_via_socket,
            self.mesh_connection.events.send_via_mesh,
            "MESH",
        )
        socket_thread = threading.Thread(
            target=trio.run, args=[socket.start_server], daemon=True
        )
        socket_thread.start()

    def start_connection(self):
        # start the outbound connection to the REMOTE C-Lightning node
        socket = TrioSocket(
            self.mesh_connection.events.send_via_socket,
            self.mesh_connection.events.send_via_mesh,
            "GATEWAY",
        )
        socket_thread = threading.Thread(target=socket.start_client, daemon=True)
        socket_thread.start()


def main(name, offgrid=1):
    node = LightningTenna(name, offgrid)
    # temporary main loop
    print("use `ctrl + c` to exit")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        ...


if __name__ == "__main__":
    arguments = docopt(__doc__)
    if arguments["--gateway"]:
        main("GATEWAY", offgrid=0)
    if arguments["--mesh"]:
        main("MESH", offgrid=1)
