from connection import Connection
from config import CONFIG


c = Connection()
c.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
c.set_gid(int(CONFIG["gotenna"]["DEBUG_GID"]))
c.set_geo_region(int(CONFIG["gotenna"]["GEO_REGION"]))

