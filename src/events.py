import queue

from utilities import de_segment, handle_event, handle_text_msg


class Events:
    def __init__(self):
        self.msg = queue.Queue()
        self.msg._name = "msg_events"
        self.device_present = queue.LifoQueue()
        self.device_present._name = "device_present_events"
        self.connect = queue.LifoQueue()
        self.connect._name = "connect_events"
        self.disconnect = queue.LifoQueue()
        self.disconnect._name = "disconnect_events"
        self.status = queue.LifoQueue()
        self.status._name = "status_events"
        self.group_create = queue.LifoQueue()
        self.group_create._name = "group_create_events"
        self.callback = queue.LifoQueue()
        self.callback._name = "callback_events"
        self.jumbo = []
        self.jumbo_len = 0
        self.send_via_socket = queue.Queue()
        self.send_via_mesh = queue.Queue()

    def get_all_connection(self):
        """Get all connect, disconnect and device present messages
        Returns a dict of queues, and their respective messages as a list for each queue
        """
        queues = [self.device_present, self.connect, self.disconnect]
        result = {}

        for q in queues:
            lst = []
            while not q.empty():
                lst.append(handle_event(q.get()))
            result[q._name] = lst

        return result

    def get_all_messages(self):
        msgs = []
        while not self.msg.empty():
            msgs.append(self.msg.get())
        return msgs

    def filter_messages(self, msgs, jumbo=False):
        returned_msgs = []
        for msg in msgs:
            if not jumbo:
                if not msg.message.payload.message.startswith("sm/"):
                    returned_msgs.append(msg)
                else:
                    self.msg.put(msg)
            if jumbo:
                if msg.message.payload.message.startswith("sm/"):
                    returned_msgs.append(msg)
                else:
                    self.msg.put(msg)
        return returned_msgs

    def get_text_messages(self):
        """Returns a dict, where the first entry contains a list of messages received
        from newest to oldest"""
        msgs = []
        result = {self.msg._name: msgs}

        m = self.get_all_messages()
        m2 = self.filter_messages(m)
        for msg in m2:
            msgs.append(handle_text_msg(msg))
        result[self.msg._name] = msgs
        return result

    def get_jumbo_message(self):
        m = self.get_all_messages()
        m2 = self.filter_messages(m, jumbo=True)
        message_list = [msg.message.payload.message for msg in m2]
        message_list.sort()
        return de_segment(message_list)

    def get_all_callback(self):
        """Returns a dict, where the first entry contains a list of callback messages
        received from newest to oldest"""
        msgs = []
        result = {self.callback._name: msgs}
        while not self.callback.empty():
            msgs.append((self.callback.get()))
        result[self.callback._name] = msgs
        return result

    def clear_all_messages(self):
        self.__init__()

    def init_jumbo(self):
        self.jumbo = []
        self.jumbo_len = 0
