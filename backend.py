import re
import queue

from db_table import *
from message_q import *


class BeProcessor:

    def process_list_cmd(self, msg: dict, b2f_q: queue.Queue):
        pass

    def process_extended_cmd(self, msg: dict, b2f_q: queue.Queue):
        pass

    def process_get_cmd(self, msg: dict, b2f_q: queue.Queue):
        pass

    def process_info_cmd(self, msg: dict, b2f_q: queue.Queue):
        pass

    @staticmethod
    def process_set_cmd(req: dict, b2f_q: queue.Queue):
        blog = req['blog']
        station = req['station']
        if len(blog) > 0:
            if len(station) > 0:
                s = DbTable('status')
                s.update(where=None, value_dictionary={'selected_blog': blog})
                s.update(where=None, value_dictionary={'selected_station': station})

                # update the selected row
                b = DbTable('blogs')
                b.update(where=None, value_dictionary={'is_selected': 0})
                b.update(where=f"blog='{blog}' AND station='{station}'", value_dictionary={'is_selected': 1})

                s.update(where=None, value_dictionary={'cli_updated': time.time()})
                s.update(where=None, value_dictionary={'blogs_updated': time.time()})

                # send OK back to the frontend
                rsp = B2fMessage()
                rsp.clone_req_msg(req)
                rsp.msg['rc'] = 0
                b2f_q.put(rsp.msg)

    def process_config_cmd(self, msg: dict, b2f_q: queue.Queue):
        pass

    def process_scan_cmd(self, msg: dict, b2f_q: queue.Queue):
        pass

    def preprocess(self, msg: dict, b2f_q: queue.Queue):

        if msg['cmd'] == 'L':
            self.process_list_cmd(msg, b2f_q)
        elif msg['cmd'] == 'E':
            self.process_extended_cmd(msg, b2f_q)
        elif msg['cmd'] == 'G':
            self.process_get_cmd(msg, b2f_q)
        elif msg['cmd'] == 'I':
            self.process_info_cmd(msg, b2f_q)
        elif msg['cmd'] == 'S':
            self.process_set_cmd(msg, b2f_q)
        elif msg['cmd'] == 'C':
            self.process_config_cmd(msg, b2f_q)
        elif msg['cmd'] == 'P':
            self.process_scan_cmd(msg, b2f_q)

    def check_for_msg(self, f2b_q: queue.Queue, b2f_q: queue.Queue):
        try:
            msg = f2b_q.get(block=True, timeout=0.2)
            if msg:
                self.preprocess(msg, b2f_q)
                f2b_q.task_done()
        except queue.Empty:
            pass  # nothing on the queue - do nothing


class Backend:

    proc = BeProcessor()

    def __init__(self):
        pass

    def backend_loop(self, f2b_q: queue.Queue, b2f_q: queue.Queue):
        while True:
            # check for f2b message and process
            self.proc.check_for_msg(f2b_q, b2f_q)
    
            # check for js8call message
    
            # run optimizing algorithms, e.g. harvesting info heard and caching

        pass
