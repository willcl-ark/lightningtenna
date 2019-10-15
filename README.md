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

    1) Must be at commit [v0.7.3rc1](https://github.com/ElementsProject/lightning/tree/v0.7.3rc1) on MESH and GATEWAY
    
    1) Apply the following changes to source code before compiling: 
    
        MESH only: [Increase HTLC Timeout](https://github.com/willcl-ark/lightning/commit/334b285fb2a9cfa9a783e670de3500779bbc1b2e) 
        
        MESH and GATEWAY [Fully Suppress Gossip](https://github.com/willcl-ark/lightning/commit/3ee42f625e76a38aa659354a26a5321d655fb679)
    

1) Both instances of C-Lightning should be ./configured using `--enable-developer` flag in order to permit the `lightning-cli dev-suppress-gossip` command.

1) Before first start, modify the values in example_config.ini as appropriate.

1) MESH should ideally have a single peer and single channel open in C-Lightning.

1) On MESH, ensure C-Lightning is not running.

1) On REMOTE start C-Lightning. Issue RPC command: `lightning-cli dev-suppress-gossip`

1) On MESH, start the python mesh client: `python lightningtenna.py --mesh`, follow the prompts, then power on goTenna (a) and await connection messages.

1) On GATEWAY (can be same machine for testing) start the gateway client `python lightningtenna.py --gatway`, power on goTenna (b) and await connection messages.

1) On MESH start C-Lightning.

1) Watch them communicate via mesh network proxy.

    N.B: Only mesh transmissions will be hexdumped to the terminal output. 

1) Pay an invoice. If testing, you can use `python testpay.py` to grab a testnet blockstream satellite invoice and try to pay it using Lighting-rpc.