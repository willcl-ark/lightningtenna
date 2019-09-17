import base58
import socket
import threading

from utilities import hexdump


MAGIC = "clight"


def connecting_socket(conn, host, port):
    # start a connecting socket to the lightning channel counterparty
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        while True:
            # if message buffered in the queue, send it:
            if not conn.events.socket_queue.empty():
                msg = conn.events.socket_queue.get()
                s.sendall(msg)
            # listen for any data received to socket and send it over the mesh
            data = s.recv(1024)
            hexdump(data)
            if not data:
                break
            final_data = MAGIC.encode() + data
            conn.send_jumbo((base58.b58encode_check(final_data)).decode())


def listening_socket(conn, lhost, lport):
    # start a listening socket for C-Lightning to connect to
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((lhost, lport))
        s.listen()
        socket_conn, addr = s.accept()
        with socket_conn:
            print("Connected by", addr)
            while True:
                # check the queue for messages to send
                if not conn.events.socket_queue.empty():
                    msg = conn.events.socket_queue.get()
                    socket_conn.sendall(msg)
                # listen for data received to socket and send it over mesh
                data = socket_conn.recv(1024)
                if not data:
                    break
                # print the data to the console
                hexdump(data)
                # add magic bytes to it
                final_data = MAGIC.encode() + data
                # send it via a mesh broadcast
                conn.send_jumbo((base58.b58encode_check(final_data)).decode())


def start_socket(conn, host, port, listen=0):
    if listen == 0:
        conn.socket = threading.Thread(
            target=connecting_socket, args=[conn, host, port]
        )
        conn.socket.start()
    elif listen == 1:
        conn.socket = threading.Thread(target=listening_socket, args=[conn, host, port])
        conn.socket.start()
    else:
        print("error starting socket")
