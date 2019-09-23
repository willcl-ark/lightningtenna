import select
import socket
import queue
import time

from utilities import hexdump, print_timer, naturalsize


LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 9733
REMOTE_IP = "77.98.116.8"
REMOTE_PORT = 9733

ART_DELAY = 12


inputs = []
outputs = []
message_queues = {}
send_times = {}

# Server setup -- will accept new connection "local" and add it to select
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(False)
server.bind((LOCAL_IP, LOCAL_PORT))
server.listen(5)
# hack to wait for local connection
local = None
while True:
    try:
        local, client_address = server.accept()
        local.setblocking(False)
        inputs.append(local)
        message_queues[local] = queue.Queue()
        send_times[local] = []
        break
    except BlockingIOError:
        time.sleep(1)
        pass


# remote setup -- will create an outbound socket
remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
remote.connect((REMOTE_IP, REMOTE_PORT))
inputs.append(remote)
outputs.append(remote)
message_queues[remote] = queue.Queue()
send_times[remote] = []


while inputs:
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
    for s in readable:
        if s is server:
            local, client_address = s.accept()
            local.setblocking(0)
            inputs.append(local)
            message_queues[local] = queue.Queue()
        else:
            data = s.recv(210)
            if data:
                print(f"\nRead {naturalsize(len(data))} data from {s.getsockname()}:")
                hexdump(data)
                if s is local:
                    message_queues[remote].put(data)
                else:
                    message_queues[local].put(data)
                if s not in outputs:
                    outputs.append(s)
            else:
                pass
                # if s in outputs:
                #     outputs.remove(s)
                # inputs.remove(s)
                # print(f"Closing {s.getsockname()}")
                # s.close()
                # del message_queues[s]

    for s in writable:
        try:
            next_msg = message_queues[s].get_nowait()
        except queue.Empty:
            pass
            # outputs.remove(s)
        else:
            print(f"Sending {naturalsize(len(next_msg))} data to {s.getsockname()}\n")
            # delay hack:
            if len(send_times[s]) == 0:
                pass
            else:
                wait = int((send_times[s][-1] + ART_DELAY) - time.time()) + 1
                print_timer(wait)
            send_times[s].append(time.time())
            s.send(next_msg)

    for s in exceptional:
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()
        del message_queues[s]
