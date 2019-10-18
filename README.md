# lightningtenna

Pay a lightning invoice over goTenna mesh network

Terms:

* MESH -- the off-grid machine. Has a copy of C-Lightning installed, a Blockstream satellite connection for blockchain backend, and will relay C-Lightning messages for a single channel, over mesh network.

* GATEWAY -- has a connection to goTenna mesh network and also internet. Does not require any C-Lightning or Bitcoin blockchain capability but will act as a relay/proxy for MESH.

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


## Setup

1) C-Lightning setup:

    1) REMOTE must be at commit [v0.7.3rc2](https://github.com/ElementsProject/lightning/tree/v0.7.3rc2)
    
    1) MESH works best with additional patches, found in this fork: [v0.7.3rc2_mesh](https://github.com/willcl-ark/lightning/commits/v0.7.3rc2_mesh)
    
    ```
    git clone https://github.com/willcl-ark/lightningtenna.git
    git checkout v0.7.3rc2_mesh
    ```

1) Both instances of C-Lightning should be configured using "--enable-developer" flag in order to permit the "lightning-cli dev-suppress-gossip" command:

    `./configure --enable-developer`

1) Make C-Lightning

    `make`

1) Before first start, modify the values in example_config.ini as appropriate.

1) MESH should ideally have a single peer and single channel open in C-Lightning.

1) On MESH, ensure C-Lightning is not running.

1) On REMOTE start C-Lightning. Issue RPC command:

    `lightning-cli dev-suppress-gossip`

1) On MESH, start the python mesh client: `python lightningtenna.py --mesh`, follow the prompts, then power on goTenna (a) and await connection messages.

1) On GATEWAY (can be same machine for testing) start the gateway client `python lightningtenna.py --gatway`, power on goTenna (b) and await connection messages.

1) On MESH start C-Lightning.

1) Watch them communicate via mesh network proxy.

1) Pay an invoice. If testing, you can use `python testpay.py` to grab a testnet blockstream satellite invoice and try to pay it using Lighting-rpc.