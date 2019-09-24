from connection import Connection
from config import CONFIG


def setup_gotenna_conn(name, server=0):
    conn = Connection(name=name, server=server)
    conn.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
    if server:
        conn.set_gid(int(CONFIG["gotenna"]["DEBUG_GID"]))
    else:
        conn.set_gid(int(CONFIG["gotenna"]["GID"]))

    conn.set_geo_region(int(CONFIG["gotenna"]["GEO_REGION"]))
    return conn

