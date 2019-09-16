import base58
import sys
import trio
from itertools import count

from utilities import hexdump

HOST = "127.0.0.1"
PORT = 9733
MAGIC = b"clight"

CONNECTION_COUNTER = count()


class AsyncServer:
    def __init__(self, conn):
        self.conn = conn
        self.queue = conn.events.socket_queue

    async def sender(self, server_stream):
        print("sender: started!")
        while True:
            if self.queue.empty():
                await trio.sleep(1)
            else:
                data = self.queue.get()
                await server_stream.send_all(data)

    async def receiver(self, server_stream):
        print("[MESH] recv socket: started!")
        async for data in server_stream:
            print(f"[MESH] recv socket: got data len({len(data)}): {data}")
            hexdump(data)
            final_data = MAGIC + data
            print(f"[MESH] recv socket: sending {final_data}")
            self.conn.send_jumbo((base58.b58encode_check(final_data)).decode())
        print("[MESH] recv socket: connection closed")
        sys.exit()

    async def echo_server(self, server_stream):
        ident = next(CONNECTION_COUNTER)
        print("echo_server {}: started".format(ident))
        async with server_stream:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(self.sender, server_stream)
                nursery.start_soon(self.receiver, server_stream)

    async def start(self):
        await trio.serve_tcp(self.echo_server, PORT)
