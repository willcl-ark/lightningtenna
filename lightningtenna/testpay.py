"""
A simple script to grab a new blocksat testnet invoice and pay it using C-Lightning
"""

import os
import pprint
import random
import time

from blocksat_api import blocksat
from lightning import LightningRpc


home = os.path.expanduser("~")
l1 = LightningRpc(home + "/.lightning/lightning-rpc")


def get_blocksat_invoice():
    print("Getting a testnet blockstream invoice...")
    invoice = blocksat.place(
        random.getrandbits(10), 10000, blocksat.TESTNET_SATELLITE_API
    )
    if invoice.status_code == 200:
        print("Got one!")
        pprint.pprint(invoice.json()["lightning_invoice"]["payreq"])
        return invoice.json()["lightning_invoice"]["payreq"]
    else:
        print(f"Couldn't get invoice:\n{invoice.reason}\n{invoice.text}")
        return False


def pay_by_route(timeout=300):
    # invoice = input("Enter your BOLT11 invoice:\n")
    invoice = get_blocksat_invoice()
    if invoice:
        decoded = l1.decodepay(invoice)
        print("Decoded payment request")
        route = l1.getroute(decoded["payee"], decoded["msatoshi"], 0)["route"]
        print("Got a route")
        print("Sending HTLC update to the channel via the mesh...")
        l1.sendpay(route, decoded["payment_hash"])
        print("Sent to mesh queue successfully. Waiting for confirmation...")
        time.sleep(2)
        pprint.pprint(l1.waitsendpay(decoded["payment_hash"], timeout))
    else:
        return


pay_by_route()
