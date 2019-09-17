# lightningtenna

Pay a lightning invoice over goTenna mesh network

Terms:

* MESH -- the off-grid machine. Has a copy of C-Lightning installed, a Blockstream satellite connection for blockchain backend, and will run lightningtenna/src/MESH_client.py to relay C-Lightning messages for a single channel, over mesh network.

* GATEWAY -- has a connection to goTenna mesh network and also internet. Does not have C-Lightning or Bitcoin blockchain capability but will run lightningtenna/src/GATEWAY_client.py. A pure relay/proxy.

* REMOTE -- the remote channel counterpaty for the lightning channel MESH has open. Has C-Lightning running only.

## Setup

1) Before first start, modify the values in example_config.ini as appropriate
1) Ensure MESH has only have a single peer and single channel open in C-Lightning (actually might not matter, but certainly clearer to use like this right now)
1) Modify the entry for REMOTE peer's ip address and port in the C-Lightning database for MESH node (~/.lightning/lightningd.sqlite3). table=Peers, column=Address to: `127.0.0.1:9733`
1) Ensure REMOTE's C-Lightning is running and connected to the internet as normal.
1) on MESH, start the mesh client: `python MESH_client.py`, power on goTenna and await connection messages
1) on GATEWAY )can be same machine) start the gateway client `python GATEWAY_client.py`, power on second goTenna and await connection messages
1) watch them send messages via gotenna

...

* TODO: Pay invoice successfully :)
