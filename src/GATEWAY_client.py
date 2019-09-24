import time
from gotenna_connections import setup_gotenna_conn

gateway_connection = setup_gotenna_conn(name="GATEWAY", server=0)

try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    ...
