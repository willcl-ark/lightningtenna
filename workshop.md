# Workshop

### Pre-requisites
* Python >-=3.7

```shell script
git clone https://github.com/willcl-ark/lightning.git
cd lightning
git fetch --all --tags
git checkout v0.7.3.2rc2_mesh
./configure --enable-developer
make
```
create conf file

```shell script
touch ~/.lighting/config
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

