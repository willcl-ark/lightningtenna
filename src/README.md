# lightningtenna

Pay a lightning invoice over goTenna mesh network

Terms:

* MESH -- the off-grid machine. Has a copy of C-Lightning installed, a Blockstream satellite connection for blockchain backend, and will run lightningtenna/src/MESH_client.py to relay C-Lightning messages for a single channel, over mesh network.

* GATEWAY -- has a connection to goTenna mesh network and also internet. Does not have C-Lightning or Bitcoin blockchain capability but will run lightningtenna/src/GATEWAY_client.py. A pure relay/proxy.

* REMOTE -- the remote channel counterpaty for the lightning channel MESH has open, not GATEWAY! Has C-Lightning running only.

Optional but recommended C-Lightning `config` options:

```
# listen but don't announce
bind-addr=0.0.0.0:9734
# disable dns lookup of peers
disable-dns
# see wire messages
log-level=io
```

Miscellany:

* Both instances of C-Lightning should be ./configured using `--enable-developer` flag in order to permit the `lightning-cli dev-suppress-gossip` command.

## Setup

1) Before first start, modify the values in example_config.ini as appropriate
1) Ensure MESH has only have a single peer and single channel open in C-Lightning (technically not essential, but certainly clearer to use like this right now)
1) On MESH node, access the C-Lightning database: (~/.lightning/lightningd.sqlite3). Open the `Peers` table and find the row corresponding to REMOTE (ip address and port). Modify the `address` column to have the value `127.0.0.1:9733` 
1) Ensure REMOTE's C-Lightning is running and connected to the internet as normal.
1) Issue RPC command to REMOTE's instance of C-Lightning: `lightning-cli dev-suppress-gossip`
1) On MESH, start the mesh client: `python select_MESH.py`, power on goTenna and await connection messages.
1) On GATEWAY (can be same machine) start the gateway client `python select_GATEWAY.py`, power on second goTenna and await connection messages.
1) On MESH start C-Lightning.
1) Watch them communicate via mesh network proxy.

...

* TODO: Pay invoice successfully :)
