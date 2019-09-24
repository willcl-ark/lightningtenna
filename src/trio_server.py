from itertools import count

import trio

from config import CONFIG
from utilities import chunk_to_queue, naturalsize

PORT = int(CONFIG["lightning"]["LOCAL_SERVER_PORT"])
CHUNK_SIZE = int(CONFIG["lightning"]["RECV_SIZE"])

CONNECTION_COUNTER = count()


class AsyncServer:
    def __init__(self, conn):
        self.conn = conn
        self.socket_queue = self.conn.events.send_via_socket
        self.mesh_queue = self.conn.events.send_via_mesh

    async def sender(self, server_stream):
        """Sends messages stored in the socket queue
        """
        print("sender: started!")
        while True:
            if self.socket_queue.empty():
                await trio.sleep(0.5)
            else:
                data = self.socket_queue.get()
                print(f"[MESH] sending {naturalsize(len(data))} via socket")
                await server_stream.send_all(data)

    async def receiver(self, server_stream):
        """Receives messages from the socket and adds them to the mesh queue
        """
        print("[MESH] recv socket: started!")
        async for data in server_stream:
            print(f"[MESH] received {naturalsize(len(data))} from socket.")
            # add received data to mesh queue in 210B chunks
            chunk_to_queue(data, CHUNK_SIZE, self.mesh_queue)
        print("[MESH] recv socket: connection closed")

    async def server(self, server_stream):
        """Accepts new connections
        """
        ident = next(CONNECTION_COUNTER)
        print("[MESH] server {}: started".format(ident))
        try:
            async with server_stream:
                async with trio.open_nursery() as nursery:
                    nursery.start_soon(self.sender, server_stream)
                    nursery.start_soon(self.receiver, server_stream)
        except Exception as exc:
            print("[MESH] server {}: crashed: {!r}".format(ident, exc))

    async def start(self):
        """for each new connection to PORT, start a new "server" process to send and
        receive data
        """
        await trio.serve_tcp(self.server, PORT)
