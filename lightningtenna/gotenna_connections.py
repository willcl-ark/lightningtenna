import random

from config import CONFIG
from connection import Connection


def setup_gotenna_conn(name, server, send_to_trio, receive_from_trio):
    conn = Connection(name, send_to_trio, receive_from_trio)
    conn.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
    if server:
        conn.set_gid(
            int(
                CONFIG.get(
                    "gotenna", "DEBUG_GID", fallback=random.randint(1, 999999999)
                )
            )
        )
    else:
        conn.set_gid(
            int(CONFIG.get("gotenna", "GID", fallback=random.randint(1, 999999999)))
        )

    conn.set_geo_region(int(CONFIG.get("gotenna", "GEO_REGION", fallback=1)))
    return conn
