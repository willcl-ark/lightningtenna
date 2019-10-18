# Workshop

### Pre-requisites
* Python >-=3.7

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

get a new funding address

```shell script
cli/lightning-cli newaddr
```

fund that address with testnet coins
If you need testnet coins, ask us and we can give you some. Paste your address into:
[qrcode.me](http://goqr.me)


connect to remote node

```shell script
cli/lightning-cli connect 032bced86b432c62e89e02e67d460e1765a14b9701b247f9614aa6ebc4f085151a@77.98.116.8:9733
```

open a channel with remote node, replace amount (in satoshis) if you like. leave word urgent for faster confirmations.

```shell script
cli/lightning-cli fundchannel 032bced86b432c62e89e02e67d460e1765a14b9701b247f9614aa6ebc4f085151a 1000000 urgent
```

wait for channel confirmation. 1 Block on testnet. to check:

```shell script
cli/lightning-cli listfunds
```

stop c-lightning

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

Follow lightningtenna setup instructions from # 4:

[Lightningtenna setup instructions](https://github.com/willcl-ark/lightningtenna/blob/master/README.md)


