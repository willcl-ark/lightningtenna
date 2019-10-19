import config
import connection

cnf = config.CONFIG



def setup_gotenna_conn(name, send_to_trio, receive_from_trio, gid):
    conn = connection.Connection(name, send_to_trio, receive_from_trio)
    if config.UBER:
        conn.sdk_token(cnf["gotenna"]["UBER_TOKEN"])
    else:
        conn.sdk_token(cnf["gotenna"]["SDK_TOKEN"])
    conn.set_gid(gid)
    conn.set_geo_region(int(cnf.get("gotenna", "GEO_REGION", fallback=2)))
    return conn
