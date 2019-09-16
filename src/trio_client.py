import base58
import sys
import trio

from utilities import hexdump


HOST = "77.98.116.8"
PORT = 9733
MAGIC = "clight"


class AsyncClient:
    def __init__(self, conn):
        self.conn = conn
        self.queue = conn.events.socket_queue

    async def sender(self):
        print("sender: started!")
        while True:
            if self.queue.empty():
                await trio.sleep(1)
            else:
                data = self.queue.get()
                final_data = MAGIC.encode() + data
                print("sender: sending {!r}".format(final_data))
                self.conn.send_jumbo((base58.b58encode_check(final_data)).decode())

    async def receiver(self, client_stream):
        print("receiver: started!")
        async for data in client_stream:
            print("receiver: got data:")
            hexdump(data)
            final_data = MAGIC.encode() + data
            print("receiver: sending {!r}".format(final_data))
            self.conn.send_jumbo((base58.b58encode_check(final_data)).decode())
        print("receiver: connection closed")
        sys.exit()

    async def parent(self):
        print(f"parent: connecting to {HOST}:{PORT}")
        client_stream = await trio.open_tcp_stream(HOST, PORT)
        async with client_stream:
            async with trio.open_nursery() as nursery:
                print("parent: spawning sender...")
                nursery.start_soon(self.sender)

                print("parent: spawning receiver...")
                nursery.start_soon(self.receiver, client_stream)

    def start(self):
        trio.run(self.parent)

