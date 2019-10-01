import os
from os.path import expanduser

from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select


def get_db():
    home = expanduser("~")
    db_path = home + "/.lightning/"
    if not os.path.exists(db_path):
        print(f"Database path {db_path} not found!")
    return db_path


def populate_peers_table():
    return Table("peers", metadata, autoload=True, autoload_with=engine)


def list_peers():
    with engine.connect() as conn:
        # select the peers table
        s = select([peers])
        result = conn.execute(s)

        peer_list = []
        for row in result:
            peer_list.append(dict(row))
            # convert bytes to hex for easier id
            peer_list[-1]["node_id"] = peer_list[-1]["node_id"].hex()

        for row in peer_list:
            print(row)


def modify_peer():
    list_peers()
    to_modify = input("Enter 'id' (number) of the gateway: ('c' to cancel)")
    if to_modify == "c":
        return
    address = input(
        "What ip address should we assign them? (default: 127.0.0.1): "
        or "127.0.0.1"
    )
    port = input("What port should we assign them? (default: 9733): " or "9733")
    with engine.connect() as conn:
        up = (
            peers.update()
            .where(peers.c.id == to_modify)
            .values(address=f"{address}:{port}")
        )
        try:
            conn.execute(up)
        except IntegrityError as e:
            raise e


engine = create_engine(f"sqlite:///{get_db() + 'lightningd.sqlite3'}")
metadata = MetaData(engine)

peers = populate_peers_table()

modify_peer()
