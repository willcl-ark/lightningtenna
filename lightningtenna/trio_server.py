from itertools import count

import trio

from config import CONFIG
from utilities import chunk_to_queue, naturalsize

PORT = int(CONFIG["lightning"]["LOCAL_SERVER_PORT"])
CHUNK_SIZE = int(CONFIG["lightning"]["RECV_SIZE"])

CONNECTION_COUNTER = count()
total_sent = {}
total_received = {}


class AsyncServer:
    def __init__(self, conn):
        self.conn = conn
        self.socket_queue = self.conn.events.send_via_socket
        self.mesh_queue = self.conn.events.send_via_mesh
        self.name = '{0: <16}'.format(f"[MESH|SOCKET]")

    async def sender(self, server_stream):
        """Sends messages stored in the socket queue
        """
        id = server_stream.socket.fileno()
        total_sent[id] = 0
        print("sender: started!")
        while True:
            if self.socket_queue.empty():
                await trio.sleep(0.5)
            else:
                data = self.socket_queue.get()
                print(f"{self.name} sending {naturalsize(len(data))} via socket")
                await server_stream.send_all(data)
                total_sent[id] += len(data)
                print(
                    f"{self.name} total sent via socket: "
                    f"{naturalsize(total_sent[id])}"
                )

    async def receiver(self, server_stream):
        """Receives messages from the socket and adds them to the mesh queue
        """
        id = server_stream.socket.fileno()
        total_received[id] = 0
        print(f"{self.name} recv socket: started!")
        async for data in server_stream:
            print(f"{self.name} received {naturalsize(len(data))} from socket.")
            total_received[id] += len(data)
            print(
                f"{self.name} total received via socket: "
                f"{naturalsize(total_received[id])}"
            )
            # add received data to mesh queue in 210B chunks
            chunk_to_queue(data, CHUNK_SIZE, self.mesh_queue)
        print(f"{self.name} recv socket: connection closed")

    async def server(self, server_stream):
        """Accepts new connections
        """
        ident = next(CONNECTION_COUNTER)
        print(f"{self.name} server {ident}: started")
        try:
            async with server_stream:
                async with trio.open_nursery() as nursery:
                    nursery.start_soon(self.sender, server_stream)
                    nursery.start_soon(self.receiver, server_stream)
        except Exception as exc:
            print(f"{self.name} server {ident}: crashed: {exc}")

    async def start(self):
        """for each new connection to PORT, start a new "server" process to send and
        receive data
        """
        await trio.serve_tcp(self.server, PORT)
