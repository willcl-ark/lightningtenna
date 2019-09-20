import base58
import hashlib
import trio
from itertools import count

from utilities import hexdump, naturalsize

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
                print(f"[MESH] sender: sending {naturalsize(len(data))} via socket")
                print(f"SHA256: {hashlib.sha256(data).hexdigest()}")
                await server_stream.send_all(data)

    async def receiver(self, server_stream):
        """Receives messages from the socket and sends them out-of-band
        """
        print("[MESH] recv socket: started!")
        async for data in server_stream:
            print(f"[MESH] recv socket: received {naturalsize(len(data))} of data.")
            # throw message away if too large
            if len(data) < MAX_SIZE:
                hexdump(data)
                print(f"SHA256: {hashlib.sha256(data).hexdigest()}")
                final_data = MAGIC + data
                print(f"[MESH] recv socket: sending data to mesh network")
                # send data received from the socket out of band
                self.conn.send_jumbo((base58.b58encode_check(final_data)).decode())
            else:
                print(f"Data too large: {len(data)} discarding")
        print("[MESH] recv socket: connection closed")

    async def server(self, server_stream):
        ident = next(CONNECTION_COUNTER)
        print("server {}: started".format(ident))
        try:
            async with server_stream:
                async with trio.open_nursery() as nursery:
                    nursery.start_soon(self.sender, server_stream)
                    nursery.start_soon(self.receiver, server_stream)
        except Exception as exc:
            print("echo_server {}: crashed: {!r}".format(ident, exc))

    async def start(self):
        # for each new connection to PORT, start a new "server" process
        await trio.serve_tcp(self.server, PORT)
