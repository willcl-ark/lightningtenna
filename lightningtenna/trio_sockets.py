from itertools import count

import trio

from config import CONFIG
from utilities import chunk_and_queue, naturalsize

REMOTE_HOST = CONFIG.get("lightning", "REMOTE_PEER_IP", fallback=None)
REMOTE_PORT = int(CONFIG.get("lightning", "REMOTE_PEER_PORT", fallback=None))
SERVER_PORT = int(CONFIG.get("lightning", "LOCAL_SERVER_PORT", fallback=None))
CHUNK_SIZE = int(CONFIG.get("lightning", "RECV_SIZE", fallback=None))

CONNECTION_COUNTER = count()
total_sent = {}
total_received = {}


class TrioSocket:
    def __init__(self, socket_queue, mesh_queue, name):
        self.socket_queue = socket_queue
        self.mesh_queue = mesh_queue
        self.name = "{0: <16}".format(f"[{name}|SOCKET]")

    async def sender(self, stream):
        id = stream.socket.fileno()
        total_sent[id] = 0
        print(f"{self.name} send channel: started!")
        while True:
            if self.socket_queue.empty():
                await trio.sleep(0.5)
            else:
                data = self.socket_queue.get()
                total_sent[id] += len(data)
                print(
                    f"{self.name} sending {naturalsize(len(data))} "
                    f"Total: {naturalsize(total_sent[id])}"
                )
                await stream.send_all(data)

    async def receiver(self, stream):
        id = stream.socket.fileno()
        total_received[id] = 0
        print(f"{self.name} recv socket: started!")
        async for data in stream:
            total_received[id] += len(data)
            print(
                f"{self.name} received {naturalsize(len(data))} "
                f"Total: {naturalsize(total_received[id])}"
            )
            # add received data to mesh queue in 210B chunks
            chunk_and_queue(data, CHUNK_SIZE, self.mesh_queue)
        print(f"{self.name} recv socket: connection closed")

    async def server(self, stream):
        """Accepts new connections
        """
        ident = next(CONNECTION_COUNTER)
        print(f"{self.name} server {ident}: started")
        try:
            async with stream:
                async with trio.open_nursery() as nursery:
                    nursery.start_soon(self.sender, stream)
                    nursery.start_soon(self.receiver, stream)
        except Exception as exc:
            print(f"{self.name} server {ident}: crashed: {exc}")

    async def parent(self):
        print(f"{self.name} parent: connecting to {REMOTE_HOST}:{REMOTE_PORT}")
        client_stream = await trio.open_tcp_stream(REMOTE_HOST, REMOTE_PORT)
        async with client_stream:
            async with trio.open_nursery() as nursery:
                print(f"{self.name} parent: spawning sender...")
                nursery.start_soon(self.sender, client_stream)

                print(f"{self.name} parent: spawning {self.name} receiver...")
                nursery.start_soon(self.receiver, client_stream)

    async def start_server(self):
        """for each new connection to PORT, start a new "server" process to send and
        receive data
        """
        await trio.serve_tcp(self.server, SERVER_PORT)

    def start_client(self):
        trio.run(self.parent)
