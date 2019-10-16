"""lightningtenna.py

Usage:
  lightningtenna.py (--gateway | --mesh) [--debug] [--uber]
  lightningtenna.py --help

Options:
  --gateway     Start a gateway node
  --mesh        Start a mesh node
  --debug       Enable debug logging to console
  --uber        With protocol v2.0 SDK token enable higher throughput
  --help        Show this screen.
"""
import logging
from itertools import count

import trio
from docopt import docopt

import db
import config
import gotenna_connections
import utilities


cnf = config.CONFIG

RECV_SIZE = int(cnf["lightning"]["RECV_SIZE"])
SERVER_PORT = int(cnf["lightning"]["SERVER_PORT"])
REMOTE_HOST = cnf["lightning"]["REMOTE_HOST"]
REMOTE_PORT = int(cnf["lightning"]["REMOTE_PORT"])
CONNECTION_COUNTER = count()


logger = logging.getLogger('SERVER')


async def sender(args):
    """Sends data from the (mesh) thread, out via the socket
    """
    socket_stream, _receive_from_thread = args
    logger.info(f"send channel: started!")
    # get data from the mesh queue
    async for data in _receive_from_thread:
        # send it out via the socket
        await socket_stream.send_all(data)


async def receiver(args):
    """Receives data from the socket and sends it to the (mesh) thread
    """
    socket_stream, _send_to_thread = args
    logger.info(f"recv socket: started!")
    async for data in socket_stream:
        # add received data to thread_stream queue in RECV_SIZE sized chunks
        async for chunk in utilities.chunk_to_list(data, RECV_SIZE):
            # send it to the mesh queue
            await _send_to_thread.send(chunk)
    logger.warning(f"recv socket: connection closed")


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
    except Exception:
        logger.exception(f"server {ident}: crashed")


async def parent():
    """Makes a new outbound connection to a remote Lightning node.
    """
    global send_to_thread, receive_from_thread
    while True:
        socket_stream = await trio.open_tcp_stream(REMOTE_HOST, REMOTE_PORT)
        try:
            async with socket_stream:
                async with trio.open_nursery() as nursery:
                    nursery.start_soon(
                        sender, [socket_stream, receive_from_thread.clone()]
                    )
                    nursery.start_soon(
                        receiver, [socket_stream, send_to_thread.clone()]
                    )
        except Exception:
            logger.exception(f"parent crashed")


async def main(args):
    gateway = args[0]
    name = "GATEWAY" if gateway else "MESH"
    if gateway:
        gid = int(cnf["gotenna"]["MESH_GID"])
    else:
        gid = int(cnf["gotenna"]["GATEWAY_GID"])

    # set up the mesh connection and pass it memory channels
    # shared between all connections to the server
    mesh_connection = gotenna_connections.setup_gotenna_conn(
        f"{name}|MESH", gateway, send_to_trio.clone(), receive_from_trio.clone()
    )

    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            utilities.mesh_auto_send,
            [mesh_connection.send_private, mesh_connection.events.send_via_mesh, gid],
        )
        nursery.start_soon(
            utilities.mesh_to_socket_queue,
            [mesh_connection.events.send_via_socket, send_to_trio.clone()],
        )
        if gateway:
            await parent()
        else:
            await trio.serve_tcp(server, SERVER_PORT)


# set up memory channels between trio and mesh connections
# shared between all socket connections
send_to_thread, receive_from_trio = trio.open_memory_channel(50)
send_to_trio, receive_from_thread = trio.open_memory_channel(50)

if __name__ == "__main__":
    arguments = docopt(__doc__)
    if arguments["--debug"]:
        config.DEBUG = True
        config.debug_logging()
    if arguments["--uber"]:
        config.UBER = True
    if arguments["--gateway"]:
        trio.run(main, [True])
    if arguments["--mesh"]:
        db.modify_peer()
        trio.run(main, [False])
