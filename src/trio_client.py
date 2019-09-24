import trio

from config import CONFIG
from utilities import chunk_to_queue, naturalsize

HOST = CONFIG["lightning"]["LOCAL_SERVER_IP"]
PORT = int(CONFIG["lightning"]["LOCAL_SERVER_PORT"])
CHUNK_SIZE = int(CONFIG["lightning"]["RECV_SIZE"])


class AsyncClient:
    def __init__(self, conn):
        self.conn = conn

    async def sender(self, client_stream):
        print("[GATEWAY] send channel: started!")
        while True:
            if self.conn.events.send_via_socket.empty():
                await trio.sleep(0.5)
            else:
                data = self.conn.events.send_via_socket.get()
                print(f"[GATEWAY] sending {naturalsize(len(data))} via socket")
                await client_stream.send_all(data)

    async def receiver(self, client_stream):
        print("[GATEWAY] recv socket: started!")
        async for data in client_stream:
            print(f"[GATEWAY] received {naturalsize(len(data))} from socket")
            chunk_to_queue(data, CHUNK_SIZE, self.conn.events.send_via_mesh)
        print("[GATEWAY] recv socket: connection closed")

    async def parent(self):
        print(f"[GATEWAY] parent: connecting to {HOST}:{PORT}")
        client_stream = await trio.open_tcp_stream(HOST, PORT)
        async with client_stream:
            async with trio.open_nursery() as nursery:
                print("[GATEWAY] parent: spawning sender...")
                nursery.start_soon(self.sender, client_stream)

                print("[GATEWAY] parent: spawning [GATEWAY] receiver...")
                nursery.start_soon(self.receiver, client_stream)

    def start(self):
        trio.run(self.parent)
