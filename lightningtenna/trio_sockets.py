"""Lightningtenna.py

Usage:
  lightningtenna.py (-g | --gateway)
  lightningtenna.py (-m | --mesh)
  lightningtenna.py (-h | --help)

Options:
  -h --help        Show this screen.
  -g --gateway     Start a gateway node
  -m --mesh        Start a mesh node server

"""

from itertools import count

import trio
from docopt import docopt

from config import CONFIG
from gotenna_connections import setup_gotenna_conn
from utilities import chunk_to_list, naturalsize

REMOTE_HOST = CONFIG.get("lightning", "REMOTE_PEER_IP", fallback=None)
REMOTE_PORT = int(CONFIG.get("lightning", "REMOTE_PEER_PORT", fallback=None))
SERVER_PORT = int(CONFIG.get("lightning", "LOCAL_SERVER_PORT", fallback=None))
CHUNK_SIZE = int(CONFIG.get("lightning", "RECV_SIZE", fallback=None))

CONNECTION_COUNTER = count()
total_sent = {}
total_received = {}
name = "temp"


class TrioSocket:
    """This class takes a socket queue, a mesh queue and a name.

    It will monitor the socket queue for messages and, when it finds one will send it
    out over the socket.

    When a message is received from the socket, it will be placed onto the mesh queue.
    """

    def __init__(socket_queue, mesh_queue, name):
        socket_queue = socket_queue
        mesh_queue = mesh_queue
        name = "{0: <16}".format(f"[{name}|SOCKET]")


async def sender(socket_stream, mesh_stream):
    id = socket_stream.socket.fileno()
    total_sent[id] = 0
    print(f"{name} send channel: started!")
    # get data from the mesh queue
    async for data in mesh_stream:
        # send it out via the socket
        await socket_stream.send_all(data)
        print(
            f"{name} sending {naturalsize(len(data))} -- "
            f"Total: {naturalsize(total_sent[id])}"
        )


async def receiver(socket_stream, mesh_stream):
    id = socket_stream.socket.fileno()
    total_received[id] = 0
    print(f"{name} recv socket: started!")
    async for data in socket_stream:
        total_received[id] += len(data)
        print(
            f"{name} received {naturalsize(len(data))} -- "
            f"Total: {naturalsize(total_received[id])}"
        )
        # add received data to mesh queue in 210B chunks
        async for chunk in chunk_to_list(data, CHUNK_SIZE):
            await mesh_stream.send(chunk)
    print(f"{name} recv socket: connection closed")


async def server(socket_stream):
    """Accepts new connections
    """
    ident = next(CONNECTION_COUNTER)
    print(f"{name} server {ident}: started")
    try:
        async with socket_stream:
            async with trio.open_nursery() as nursery:
                nursery.start_soon(sender, socket_stream)
                nursery.start_soon(receiver, socket_stream)
    except Exception as exc:
        print(f"{name} server {ident}: crashed: {exc}")


async def parent(*args):
    print(f"{name} parent: connecting to {REMOTE_HOST}:{REMOTE_PORT}")
    with trio.socket.socket() as client_sock:
        await client_sock.connect((f"{REMOTE_HOST}", REMOTE_PORT))
        async with trio.open_nursery() as nursery:
            print("parent: spawning sender...")
            nursery.spawn(sender, [client_sock, args[1]])

            print("parent: spawning receiver...")
            nursery.spawn(receiver, [client_sock, args[0]])

    # client_stream = await trio.open_tcp_stream(REMOTE_HOST, REMOTE_PORT)
    # async with client_stream:
    #     async with trio.open_nursery() as nursery:
    #         print(f"{name} parent: spawning sender...")
    #         nursery.start_soon(sender, client_stream)
    #
    #         print(f"{name} parent: spawning {name} receiver...")
    #         nursery.start_soon(receiver, client_stream)


async def start_server():
    """for each new connection to PORT, start a new "server" process to send and
    receive data
    """
    await trio.serve_tcp(server, SERVER_PORT)


async def main(args):
    # create the Trio memory channels used to pass data from goTenna to the socket
    send_to_thread, receive_from_trio = trio.open_memory_channel(50)
    send_to_trio, receive_from_thread = trio.open_memory_channel(50)
    if args["--gateway"]:
        conn_args = ["GATEWAY|MESH", False, send_to_trio, receive_from_trio]
        mesh_connection = setup_gotenna_conn(*conn_args)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(parent, [send_to_thread, receive_from_thread])
    elif args["--mesh"]:
        conn_args = ["MESH|MESH", False, send_to_trio, receive_from_trio]
    else:
        return
    mesh_connection = setup_gotenna_conn(*conn_args)
    trio.run(start_server)
    return


if __name__ == "__main__":
    arguments = docopt(__doc__)
    trio.run(main, arguments)
