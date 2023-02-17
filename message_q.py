import time
import queue

f2b_q = queue.Queue(maxsize=20)
b2f_q = queue.Queue(maxsize=20)


class F2bMessage:
    msg = {'ts': 0.0, 'cmd': "", 'blog': "", 'station': "", 'frequency': 0,
           'post_id': 0, 'post_date': 0, 'op': "", 'param': "", 'rc': 0}
    # Valid cmd and other values
    # L - blog, post_id or post_date, op set to 'eq', 'gt' or 'lt': lists posts in brief format
    # E - blog, post_id or post_date, op set to 'eq', 'gt' or 'lt': lists posts in extended format
    # G - blog and post_id: gets a specific post
    # I - blog: returns information about the blog
    # S - blog: sets the selected_blog value
    # S - frequency: sets the radio frequency
    # C - operator equals the configuration item and param is the value: sets a configuration setting
    #       all configuration settings cause a change in the database settings table except for
    #       setting db_file which causes a recreation of the db_root.py file
    # P - op set to 'start' or 'stop': starts and stops a promiscuous scan
    # Note that the station that receives blog-based commands is selected by the backend based on the best SNR

    def set_cmd(self, value: str):
        self.msg['cmd'] = value

    def set_blog(self, value: str):
        self.msg['blog'] = value

    def set_station(self, value: str):
        self.msg['station'] = value

    def set_frequency(self, value: int):
        self.msg['frequency'] = value

    def set_post_id(self, value: int):
        self.msg['post_id'] = value

    def set_post_date(self, value: int):
        self.msg['post_date'] = value

    def set_op(self, value: str):
        self.msg['op'] = value

    def set_param(self, value: str):
        self.msg['param'] = value

    def set_rc(self, value: int):
        self.msg['rc'] = value

    def set_ts(self):
        self.msg['ts'] = time.time()


class B2fMessage:
    msg = {'ts': 0.0, 'cmd': "", 'blog': "", 'station': "", 'frequency': 0,
           'post_id': 0, 'post_date': 0, 'op': "", 'param': "", 'rc': 0}

    def set_cmd(self, value: str):
        self.msg['cmd'] = value

    def set_blog(self, value: str):
        self.msg['blog'] = value

    def set_station(self, value: str):
        self.msg['station'] = value

    def set_frequency(self, value: int):
        self.msg['frequency'] = value

    def set_post_id(self, value: int):
        self.msg['post_id'] = value

    def set_post_date(self, value: int):
        self.msg['post_date'] = value

    def set_op(self, value: str):
        self.msg['op'] = value

    def set_param(self, value: str):
        self.msg['param'] = value

    def set_rc(self, value: int):
        self.msg['rc'] = value

    def set_ts(self):
        self.msg['ts'] = time.time()
