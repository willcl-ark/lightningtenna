import base58
import sys
import trio
from itertools import count

from utilities import hexdump

HOST = "127.0.0.1"
PORT = 9733
MAGIC = "clight"

CONNECTION_COUNTER = count()


class AsyncServer:
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
                self.conn.send_jumbo(
                    (base58.b58encode_check(final_data)).decode()
                )

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
        # listen for incoming TCP connections
        listeners = await trio.open_tcp_listeners(PORT)
        async with trio.open_nursery() as nursery:
            print("parent: spawning sender...")
            nursery.start_soon(self.sender)

            print("parent: spawning receiver...")
            # for each new connection start a new task and run self.receiver
            await trio.serve_listeners(self.receiver, listeners)

    def start(self):
        trio.run(self.parent)

