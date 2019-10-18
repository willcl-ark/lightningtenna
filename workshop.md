# Workshop

### Pre-requisites
* Python >-=3.7

```shell script
git clone https://github.com/willcl-ark/lightning.git
cd lightning
git pull --all
git fetch --all --tags
git checkout origin/v0.7.3.2rc2_mesh
./configure --enable-developer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make
```
create conf file

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

connect to remote node

```shell script
cli/lighting-cli connect 038edc7b1838126909859d2311dfea52503ccedc7508a42dd3d962a512086909b8@77.98.116.8:9734
```

get a new funding address

```shell script
cli/lightning-cli newaddr
```

fund that address with testnet coins

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



