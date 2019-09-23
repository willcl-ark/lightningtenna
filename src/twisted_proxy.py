from twisted.internet import protocol, reactor
from utilities import hexdump, naturalsize


def _noop(data):
    return hexdump(data)


FORMAT_FN = _noop

LISTEN_PORT = 9733
DST_PORT = 9733
DST_IP = "77.98.116.8"
local_ip = "127.0.0.1"


class TCPProxyProtocol(protocol.Protocol):
    """
    TCPProxyProtocol listens for TCP connections from a
    client (eg. a phone) and forwards them on to a
    specified destination (eg. an app's API server) over
    a second TCP connection, using a ProxyToServerProtocol.

    It assumes that neither leg of this trip is encrypted.
    """

    def __init__(self):
        self.buffer = None
        self.proxy_to_server_protocol = None

    def connectionMade(self):
        """
        Called by twisted when a client connects to the
        proxy. Makes an connection from the proxy to the
        server to complete the chain.
        """
        print("Connection made from CLIENT => PROXY")
        proxy_to_server_factory = protocol.ClientFactory()
        proxy_to_server_factory.protocol = ProxyToServerProtocol
        proxy_to_server_factory.server = self

        reactor.connectTCP(DST_IP, DST_PORT, proxy_to_server_factory)

    def dataReceived(self, data):
        """
        Called by twisted when the proxy receives data from
        the client. Sends the data on to the server.

        CLIENT ===> PROXY ===> DST
        """
        print("")
        print("CLIENT ===> PROXY ===> DST")
        print(f"Received {naturalsize(len(data))}")
        print(data)
        print(FORMAT_FN(data))
        print("")
        if self.proxy_to_server_protocol:
            self.proxy_to_server_protocol.write(data)
        else:
            self.buffer = data

    def write(self, data):
        self.transport.write(data)
        # c.send_jumbo(base58.b58encode_check(data).decode())


class ProxyToServerProtocol(protocol.Protocol):
    """
    ProxyToServerProtocol connects to a server over TCP.
    It sends the server data given to it by an
    TCPProxyProtocol, and uses the TCPProxyProtocol to
    send data that it receives back from the server on
    to a client.
    """

    def connectionMade(self):
        """
        Called by twisted when the proxy connects to the
        server. Flushes any buffered data on the proxy to
        server.
        """
        print("Connection made from PROXY => SERVER")
        self.factory.server.proxy_to_server_protocol = self
        self.write(self.factory.server.buffer)
        self.factory.server.buffer = ""

    def dataReceived(self, data):
        """
        Called by twisted when the proxy receives data
        from the server. Sends the data on to to the client.

        DST ===> PROXY ===> CLIENT
        """
        print("")
        print("DST ===> PROXY ===> CLIENT")
        print(f"Received {naturalsize(len(data))}")
        print(data)
        print(FORMAT_FN(data))
        print("")
        self.factory.server.write(data)

    def write(self, data):
        if data:
            self.transport.write(data)


print(
    """
#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#
-#-#-#-#-#-RUNNING  TCP PROXY-#-#-#-#-#-
#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#

Dst IP:\t%s
Dst port:\t%d

Listen port:\t%d
Local IP:\t%s
"""
    % (DST_IP, DST_PORT, LISTEN_PORT, local_ip)
)

print(f"""Listening for requests on {local_ip}:{LISTEN_PORT}...""")

factory = protocol.ServerFactory()
factory.protocol = TCPProxyProtocol
reactor.listenTCP(LISTEN_PORT, factory)
reactor.run()
