from config import CONFIG
from connection import Connection


def setup_gotenna_conn(name, offgrid):
    """Sets up and returns a goTenna connection with a 'name' and 'offgrid' param.
    offgrid should be True for machines with no direct internet connection, e.g. MESH
    """
    conn = Connection(name=name)
    conn.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
    if offgrid:
        conn.set_gid(int(CONFIG.get("gotenna", "GID", fallback=1234567)))
    else:
        conn.set_gid(int(CONFIG.get("gotenna", "DEBUG_GID", fallback=9876543)))

    conn.set_geo_region(int(CONFIG.get("gotenna", "GEO_REGION", fallback=1)))
    return conn
