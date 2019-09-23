from connection import Connection
from config import CONFIG


def setup_gotenna_conn(name, gateway=0):
    conn = Connection(name=name)
    conn.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
    if gateway:
        conn.set_gid(int(CONFIG["gotenna"]["GID"]))
    else:
        conn.set_gid(int(CONFIG["gotenna"]["DEBUG_GID"]))

    conn.set_geo_region(int(CONFIG["gotenna"]["GEO_REGION"]))
    return conn

