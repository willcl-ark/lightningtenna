# Workshop

### Pre-requisites
* Python >-=3.6

Get Will Clark's fork of C-Lightning:

```shell script
git clone https://github.com/willcl-ark/lightning.git
cd lightning
git pull --all
git fetch --all --tags
```

Follow commands to compile C-Lightning for your architecture. Stop at `./configure`:

[Compile C-Lightning](https://github.com/ElementsProject/lightning/blob/master/doc/INSTALL.md)

```shell script
git checkout origin/v0.7.3rc2_mesh
./configure --enable-developer
make
```

create c-lightning conf file

```shell script
mkdir ~/.lightning
touch ~/.lighting/config
# use your favourite editor!
vim ~/.lightning/config
```

paste this

```
network=testnet
allow-deprecated-apis=false
bitcoin-rpcport=18332
bitcoin-rpcuser=user
bitcoin-rpcpassword=password
bitcoin-rpcconnect=95.211.225.220
bind-addr=0.0.0.0:9734
autolisten=False
log-level=debug
rescan=3
```

start lighting

```shell script
lightningd/lightningd
```

Open a new terminal window and switch to it.

Enable gossip

```shell script
cli/lightning-cli dev-suppress-gossip
```

connect to blockstream for gossip, and remote node

```shell script
cli/lightning-cli connect 039d2201586141a3fff708067aa270aa4f6a724227d5740254d4e34da262a79c2a@34.83.166.97:9735
cli/lightning-cli connect 032bced86b432c62e89e02e67d460e1765a14b9701b247f9614aa6ebc4f085151a@77.98.116.8:9733
```

get a new funding address

```shell script
cli/lightning-cli newaddr
```

fund that address with testnet coins
If you need testnet coins, ask us and we can give you some. Paste your address into:
[qrcode.me](http://goqr.me)

you can check watch for the funds arriving with:

```shell script
watch -n 5 cli/lightning-cli listfunds
```

open a channel with remote node, replace amount (in satoshis) if you like. leave word urgent for faster confirmations.

```shell script
cli/lightning-cli fundchannel 032bced86b432c62e89e02e67d460e1765a14b9701b247f9614aa6ebc4f085151a 1000000 urgent
```

wait for channel confirmation. 1 Block on testnet. to check:

```shell script
cli/lightning-cli listfunds
```

wait for gossip levels to settle down (watch terminal) and stop c-lightning

```shell script
cli/lightning-cli stop
```

Open a new terminal window. Clone lightningtenna and install requirements:

```shell script
git clone https://github.com/willcl-ark/lightningtenna.git
cd lightningtenna
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ubuntu users might also try the following:

```shell script
wget https://raw.githubusercontent.com/gotenna/PublicSDK/master/python-public-sdk/77-gotenna.rules
cp 77-gotenna.rules /etc/udev/rules.d/
udevadm control --reload
```

## MESH 
Run the mesh client:

```shell script
python lightningtenna.py --mesh
```

Follow the prompts to choose a channel to proxy through the mesh. Note, the ip address will not be restored automatically afterwards.
Next connect and power on the gotenna.

When a GATEWAY is also active, mesh can run the script in a new terminal to request a blocksat invoice (for a random message) over clearnet, and pay via lightning where the HTLCs are propagated directly through the mesh connection:

```shell script
python testpay.py
```

## GATEWAY
Run the gateway client:

```shell script
python lightningtenna.py --gateway
```



