"""lightningtenna.py

Usage:
  lightningtenna.py (-g | --gateway)
  lightningtenna.py (-m | --mesh)
  lightningtenna.py (-h | --help)

Options:
  -h --help        Show this screen.
  -g --gateway     Start a gateway node
  -m --mesh        Start a mesh node server
"""

from docopt import docopt
import trio
from itertools import count
from config import CONFIG
from gotenna_connections import setup_gotenna_conn
from utilities import chunk_to_list, mesh_auto_send, mesh_to_socket_queue

RECV_SIZE = int(CONFIG["lightning"]["RECV_SIZE"])
SERVER_PORT = int(CONFIG["lightning"]["SERVER_PORT"])
REMOTE_HOST = CONFIG["lightning"]["REMOTE_HOST"]
REMOTE_PORT = int(CONFIG["lightning"]["REMOTE_PORT"])
CONNECTION_COUNTER = count()


async def sender(args):
    """Sends data from the (mesh) thread, out via the socket
    """
    socket_stream, receive_from_thread = args
    print(f"send channel: started!")
    # get data from the mesh queue
    async for data in receive_from_thread:
        # send it out via the socket
        await socket_stream.send_all(data)


async def receiver(args):
    """Receives data from the socket and sends it to the (mesh) thread
    """
    socket_stream, send_to_thread = args
    print(f"recv socket: started!")
    async for data in socket_stream:
        # add received data to thread_stream queue in 210B chunks
        async for chunk in chunk_to_list(data, RECV_SIZE):
            print(data)
            await send_to_thread.send(chunk)
    print(f"recv socket: connection closed")


async def server(socket_stream):
    """A server to accept new connections from local lightning node.
    """
    global send_to_thread, receive_from_thread
    ident = next(CONNECTION_COUNTER)
    try:
        async with socket_stream:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(sender, [socket_stream, receive_from_thread.clone()])
                nursery.start_soon(receiver, [socket_stream, send_to_thread.clone()])
    except Exception as exc:
        print(f"server {ident}: crashed: {exc}")


async def parent():
    """Makes a new outbound connection to a remote Lightning node.
    """
    global send_to_thread, receive_from_thread
    while True:
        socket_stream = await trio.open_tcp_stream(REMOTE_HOST, REMOTE_PORT)
        try:
            async with socket_stream:
                async with trio.open_nursery() as nursery:
                    nursery.start_soon(sender, [socket_stream, receive_from_thread.clone()])
                    nursery.start_soon(receiver, [socket_stream, send_to_thread.clone()])
        except Exception as exc:
            print(f"parent crashed: {exc}")


async def main(args):
    gateway = args[0]
    name = "GATEWAY" if gateway else "MESH"
    global send_to_trio, receive_from_trio

    # set up the mesh connection and pass it memory channels
    # shared between all connections to the server
    mesh_connection = setup_gotenna_conn(
        f"{name}|MESH", False, send_to_trio.clone(), receive_from_trio.clone()
    )
    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            mesh_auto_send,
            [mesh_connection.send_broadcast, mesh_connection.events.send_via_mesh],
        )
        nursery.start_soon(
            mesh_to_socket_queue,
            [mesh_connection.events.send_via_socket, send_to_trio.clone()],
        )
        if gateway:
            await parent()
        else:
            await trio.serve_tcp(server, SERVER_PORT)


# set up memory channels between trio and mesh connections
# shared between all instances
send_to_thread, receive_from_trio = trio.open_memory_channel(50)
send_to_trio, receive_from_thread = trio.open_memory_channel(50)

if __name__ == "__main__":
    arguments = docopt(__doc__)
    if arguments["--gateway"]:
        trio.run(main, [True])
    if arguments["--mesh"]:
        trio.run(main, [False])
