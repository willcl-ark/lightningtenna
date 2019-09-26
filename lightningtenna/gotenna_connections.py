from config import CONFIG
from connection import Connection


def setup_gotenna_conn(name, server=0):
    conn = Connection(name=name, server=server)
    conn.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
    if server:
        conn.set_gid(int(CONFIG.get("gotenna", "DEBUG_GID", fallback=1234567)))
    else:
        conn.set_gid(int(CONFIG.get("gotenna", "GID", fallback=9876543)))

    conn.set_geo_region(int(CONFIG.get("gotenna", "GEO_REGION", fallback=1)))
    return conn
