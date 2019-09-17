from connection import Connection
import pickle
from scapy.all import *
import base58
from config import CONFIG


c = Connection()
c.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
c.set_gid(int(CONFIG["gotenna"]["DEBUG_GID"]))
c.set_geo_region(int(CONFIG["gotenna"]["GEO_REGION"]))


msg = {"big random dictionary or something here": "probably something here too"}

packet_msg = IP(dst="192.168.100.123")/TCP()/"from scapy packet"


def send_packet(message):
    global c
    p_msg = pickle.dumps(message)
    b58_msg = base58.b58encode(p_msg)
    c.send_broadcast(str(b58_msg))


def send_jumbo_packet(message):
    global c
    p_msg = pickle.dumps(message)
    b58_msg = base58.b58encode(p_msg)
    c.send_jumbo(str(b58_msg))
