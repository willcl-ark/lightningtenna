# lightningtenna

Pay a lightning invoice over goTenna mesh network

Terms:

* MESH -- the off-grid machine. Has a copy of C-Lightning installed, a Blockstream satellite connection for blockchain backend, and will run lightningtenna/src/MESH_client.py to relay C-Lightning messages for a single channel, over mesh network.

* GATEWAY -- has a connection to goTenna mesh network and also internet. Does not have C-Lightning or Bitcoin blockchain capability but will run lightningtenna/src/GATEWAY_client.py. A pure relay/proxy.

* REMOTE -- the remote channel counterpaty for the lightning channel MESH has open, not GATEWAY! Has C-Lightning running only.

Optional but recommended C-Lightning `config` options:

```
# listen but don't announce
bind-addr=0.0.0.0:9733
# disable dns lookup of peers
disable-dns
# see wire messages
log-level=io
```

Miscellany:

* Both instances of C-Lightning should be ./configured using `--enable-developer` flag in order to permit the `lightning-cli dev-suppress-gossip` command.

## Setup

1) Before first start, modify the values in example_config.ini as appropriate

1) MESH and REMOTE C-Lightning must be compiled with configure flag `--enable-developer`

1) MESH should have a single peer and single channel open in C-Lightning

1) On MESH, ensure C-Lightning is not running

1) On MESH, in the C-Lightning source code modify `lightningd/peer_htlcs.c` and on Line 468, change `30` to `300` to give us a longer timeout on HTLCs. Now recompile C-Lightning (don't forget `./configure` flags!) with this patch.

1) On MESH, access the C-Lightning database: (~/.lightning/lightningd.sqlite3). Open the `Peers` table and find the row corresponding to REMOTE (ip address and port). Modify the `address` column to have the value `127.0.0.1:9733`, or whatever you set in `example_config.ini` previously

1) On REMOTE start C-Lightning. Issue RPC command: `lightning-cli dev-suppress-gossip`

1) On MESH, start the python mesh client: `python MESH_client.py`, power on goTenna (a) and await connection messages.

1) On GATEWAY (can be same machine for testing) start the gateway client `python GATEWAY_client.py`, power on goTenna (b) and await connection messages.

1) On MESH start C-Lightning.

1) Watch them communicate via mesh network proxy.

1) Pay an invoice.