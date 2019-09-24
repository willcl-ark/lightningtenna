import time
from gotenna_connections import setup_gotenna_conn

mesh_connection = setup_gotenna_conn(name="MESH", server=1)


try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    ...
