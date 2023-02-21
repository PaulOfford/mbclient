import time


class F2bMessage:
    msg = {'ts': 0.0, 'req_ts': 0.0, 'cmd': "", 'blog': "", 'station': "", 'frequency': 0,
           'post_id': 0, 'post_date': 0, 'op': "", 'param': "", 'rc': 0}
    # Valid cmd and other values
    # L - blog, post_id or post_date, op set to 'eq', 'gt' or 'lt': lists posts in brief format
    # E - blog, post_id or post_date, op set to 'eq', 'gt' or 'lt': lists posts in extended format
    # G - blog and post_id: gets a specific post
    # I - blog: returns information about the blog
    # S - blog and station: sets the selected_blog value
    # S - frequency: sets the radio frequency
    # C - operator equals the configuration item and param is the value: sets a configuration setting
    #       all configuration settings cause a change in the database settings table except for
    #       setting db_file which causes a recreation of the db_root.py file
    # P - op set to 'start' or 'stop': starts and stops a promiscuous scan
    # Note that the station that receives blog-based commands is selected by the backend based on the best SNR

    def set_ts(self):
        self.msg['ts'] = time.time()

    def set_req_ts(self, value: float):
        self.msg['req_ts'] = value

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


class B2fMessage:
    msg = {'ts': 0.0, 'req_ts': 0.0, 'cmd': "", 'blog': "", 'station': "", 'frequency': 0,
           'post_id': 0, 'post_date': 0, 'op': "", 'param': "", 'rc': 0}

    def set_ts(self):
        self.msg['ts'] = time.time()

    def set_req_ts(self, value: float):
        self.msg['req_ts'] = value

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

    def clone_req_msg(self, req: dict):
        self.set_ts()
        self.set_req_ts(req['ts'])
        self.set_cmd(req['cmd'])
        self.set_blog(req['blog'])
        self.set_station(req['station'])
        self.set_frequency(req['frequency'])
        self.set_post_id(req['post_id'])
        self.set_post_date(req['post_date'])
        self.set_op(req['op'])
        self.set_param(req['param'])
        self.set_rc(req['rc'])
