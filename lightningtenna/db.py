import os
from os.path import expanduser

from sqlalchemy import Column, MetaData, Table, create_engine
from sqlalchemy.sql import select


def get_db():
    home = expanduser("~")
    db_path = home + "/.lightning/"
    if not os.path.exists(db_path):
        print(f"Database path {db_path} not found!")
    return db_path


def list_peers():
    # select the peers table
    s = select([peers])
    result = conn.execute(s)

    peer_list = []
    for row in result:
        peer_list.append(dict(row))
        # convert bytes to hex for easier id
        peer_list[-1]["node_id"] = peer_list[-1]["node_id"].hex()

    print(peer_list)


# TODO: revert to lightningd.sqlite3!!
engine = create_engine(f"sqlite:///{get_db() + 'lightningd2.sqlite3'}")
metadata = MetaData(engine)
conn = engine.connect()

# reflect the 'peers' table
peers = Table("peers", metadata, autoload=True, autoload_with=engine)

list_peers()
