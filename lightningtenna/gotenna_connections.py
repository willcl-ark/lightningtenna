import random

import config
import connection

cnf = config.CONFIG
min_GID = 10000000
max_GID = 999999999


def setup_gotenna_conn(name, gateway, send_to_trio, receive_from_trio):
    conn = connection.Connection(name, send_to_trio, receive_from_trio)
    if config.UBER:
        conn.sdk_token(cnf["gotenna"]["UBER_TOKEN"])
    else:
        conn.sdk_token(cnf["gotenna"]["SDK_TOKEN"])
    if gateway:
        conn.set_gid(
            int(
                cnf.get(
                    "gotenna", "GATEWAY_GID", fallback=random.randint(min_GID, max_GID)
                )
            )
        )
    else:
        conn.set_gid(
            int(
                cnf.get(
                    "gotenna", "MESH_GID", fallback=random.randint(min_GID, max_GID)
                )
            )
        )
    conn.set_geo_region(int(cnf.get("gotenna", "GEO_REGION", fallback=2)))
    return conn
