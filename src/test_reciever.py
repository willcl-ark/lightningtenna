import time
from config import CONFIG
from connection import Connection

c = Connection()
c.sdk_token(CONFIG["gotenna"]["SDK_TOKEN"])
c.set_gid(int(CONFIG["gotenna"]["GID"]))
c.set_geo_region(int(CONFIG["gotenna"]["GEO_REGION"]))

try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    ...
