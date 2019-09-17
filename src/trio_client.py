import base58
import sys
import trio

from config import CONFIG
from utilities import hexdump, naturalsize


HOST = CONFIG["lightning"]["REMOTE_PEER_IP"]
PORT = int(CONFIG["lightning"]["REMOTE_PEER_PORT"])
MAGIC = b"clight"
MAX_SIZE = 1800


class AsyncClient:
    def __init__(self, conn):
        self.conn = conn
        self.queue = conn.events.socket_queue

    async def sender(self, client_stream):
        print("[GATEWAY] send channel: started!")
        while True:
            if self.queue.empty():
                await trio.sleep(1)
            else:
                data = self.queue.get()
                print(f"[GATEWAY] send channel: sending {naturalsize(len(data))}")
                await client_stream.send_all(data)

    async def receiver(self, client_stream):
        print("[GATEWAY] recv socket: started!")
        async for data in client_stream:
            print("[GATEWAY] recv socket: got data:")
            if len(data) < MAX_SIZE:
                hexdump(data)
                final_data = MAGIC + data
                print("[GATEWAY] recv socket: sending data to mesh network")
                self.conn.send_jumbo((base58.b58encode_check(final_data)).decode())
        else:
            print("Data too large, discarding")
        print("[GATEWAY] recv socket: connection closed")
        # TODO: need to refactor so that connection will be retried if lost
        sys.exit()

    async def parent(self):
        print(f"[GATEWAY] parent: connecting to {HOST}:{PORT}")
        client_stream = await trio.open_tcp_stream(HOST, PORT)
        async with client_stream:
            async with trio.open_nursery() as nursery:
                print("[GATEWAY] parent: spawning sender...")
                nursery.start_soon(self.sender, client_stream)

                print("[GATEWAY] parent: spawning [GATEWAY] recv socket...")
                nursery.start_soon(self.receiver, client_stream)

    def start(self):
        trio.run(self.parent)
