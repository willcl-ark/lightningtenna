# Workshop

### Pre-requisites
* Python >-=3.7

```shell script
git clone https://github.com/willcl-ark/lightning.git
cd lightning
git pull --all
git fetch --all --tags
```

Follow commands to get DEPENDENCIES for your architecture. Don't `./configure` or `make` yet!:

[build c-lightning](https://github.com/ElementsProject/lightning/blob/master/doc/INSTALL.md)

```shell script
git checkout origin/v0.7.3rc2_mesh
./configure --enable-developer
make
```

create c-lightning conf file

```shell script
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

enable gossip

```shell script
cli/lightning-cli dev-suppress-gossip
```

get a new funding address

```shell script
cli/lightning-cli newaddr
```

fund that address with testnet coins

connect to remote node

```shell script
cli/lighting-cli connect 038edc7b1838126909859d2311dfea52503ccedc7508a42dd3d962a512086909b8@77.98.116.8:9734
```

open a channel with remote node, replace amount (in satoshis) if you like. leave word urgent for faster confirmations.

```shell script
cli/lightning-cli fundchannel 038edc7b1838126909859d2311dfea52503ccedc7508a42dd3d962a512086909b8 1000000 urgent
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


