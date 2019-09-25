import trio

from config import CONFIG
from utilities import chunk_to_queue, naturalsize

HOST = CONFIG["lightning"]["REMOTE_PEER_IP"]
PORT = int(CONFIG["lightning"]["REMOTE_PEER_PORT"])
CHUNK_SIZE = int(CONFIG["lightning"]["RECV_SIZE"])

total_sent = {}
total_received = {}


class AsyncClient:
    def __init__(self, conn):
        self.conn = conn
        self.socket_queue = self.conn.events.send_via_socket
        self.mesh_queue = self.conn.events.send_via_mesh
        self.name = '{0: <16}'.format(f"[GATEWAY|SOCKET]")

    async def sender(self, client_stream):
        id = client_stream.socket.fileno()
        total_sent[id] = 0
        print(f"{self.name} send channel: started!")
        while True:
            if self.socket_queue.empty():
                await trio.sleep(0.5)
            else:
                data = self.socket_queue.get()
                print(f"{self.name} sending {naturalsize(len(data))} via socket")
                await client_stream.send_all(data)
                total_sent[id] += len(data)
                print(
                        f"{self.name} total sent via socket: "
                        f"{naturalsize(total_sent[id])}"
                )

    async def receiver(self, client_stream):
        id = client_stream.socket.fileno()
        total_received[id] = 0
        print(f"{self.name} recv socket: started!")
        async for data in client_stream:
            print(f"{self.name} received {naturalsize(len(data))} from socket")
            total_received[id] += len(data)
            print(
                    f"{self.name} total received via socket: "
                    f"{naturalsize(total_received[id])}"
            )
            # add received data to mesh queue in 210B chunks
            chunk_to_queue(data, CHUNK_SIZE, self.mesh_queue)
        print(f"{self.name} recv socket: connection closed")

    async def parent(self):
        print(f"{self.name} parent: connecting to {HOST}:{PORT}")
        client_stream = await trio.open_tcp_stream(HOST, PORT)
        async with client_stream:
            async with trio.open_nursery() as nursery:
                print(f"{self.name} parent: spawning sender...")
                nursery.start_soon(self.sender, client_stream)

                print(f"{self.name} parent: spawning {self.name} receiver...")
                nursery.start_soon(self.receiver, client_stream)

    def start(self):
        trio.run(self.parent)
