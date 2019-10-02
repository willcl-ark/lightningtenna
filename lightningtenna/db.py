import os
from os.path import expanduser

from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from utilities import get_id_addr_port


def get_db():
    """Get an existing C-Lightning DB path
    """
    home = expanduser("~")
    db_path = home + "/.lightning/"
    if not os.path.exists(db_path):
        print(f"Database path {db_path} not found!")
    return db_path


def populate_peers_table():
    """Grab the contents of the peers table
    """
    return Table("peers", metadata, autoload=True, autoload_with=engine)


def list_peers():
    """List each peer in the table, converting node_id binary blobs to hex for
    easier id
    """
    with engine.connect() as conn:
        # select the peers table
        s = select([peers])
        result = conn.execute(s)

        print("Got peers list from C-Lightning database:\n")

        peer_list = []
        for row in result:
            peer_list.append(dict(row))
            # convert node_id bytes to hex
            peer_list[-1]["node_id"] = peer_list[-1]["node_id"].hex()

        for row in peer_list:
            print(f"\n{row}")
        print("\n")


def modify_peer():
    """Choose a peer from the db to modify and update the values
    """
    # TODO: we should save existing values first, so that we can restore them
    #   afterwards.
    list_peers()
    try:
        to_modify, address, port = get_id_addr_port()
    except TypeError:
        return

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
