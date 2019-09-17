import base58
import sys
import trio
from itertools import count

from utilities import hexdump

HOST = "127.0.0.1"
PORT = 9733
MAGIC = b"clight"
# largest observed Update HTLC message was 1540 Bytes
MAX_SIZE = 1800

CONNECTION_COUNTER = count()


class AsyncServer:
    def __init__(self, conn):
        self.conn = conn
        self.queue = conn.events.socket_queue

    async def sender(self, server_stream):
        """Sends messages stored in the queue out via the socket
        """
        print("sender: started!")
        while True:
            if self.queue.empty():
                await trio.sleep(1)
            else:
                data = self.queue.get()
                await server_stream.send_all(data)

    async def receiver(self, server_stream):
        """Receives messages from the socket and sends them out-of-band
        """
        print("[MESH] recv socket: started!")
        async for data in server_stream:
            print(f"[MESH] recv socket: got data len({len(data)}): {data}")
            # throw message away if too large
            if len(data) < MAX_SIZE:
                hexdump(data)
                final_data = MAGIC + data
                print(f"[MESH] recv socket: sending {final_data}")
                # send data received from the socket out of band
                self.conn.send_jumbo((base58.b58encode_check(final_data)).decode())
            else:
                print("Data too large, discarding")
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
        # for each new connection to PORT, start a new "server" process
        await trio.serve_tcp(self.server, PORT)
