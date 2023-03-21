from status import *


class GuiMessage:

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

    ts = 0.0
    req_ts = 0.0
    cli_input = ""
    cmd = ""
    blog = ""
    station = ""
    frequency = 0
    post_id = 0
    post_date = 0
    op = ""
    param = ""
    rc = 0

    def set_ts(self):
        self.ts = time.time()

    def set_req_ts(self, value: float):
        self.req_ts = value

    def set_cli_input(self, value: str):
        self.cli_input = value

    def set_cmd(self, value: str):
        self.cmd = value

    def set_blog(self, value: str):
        self.blog = value

    def set_station(self, value: str):
        self.station = value

    def set_frequency(self, value: int):
        self.frequency = value

    def set_post_id(self, value: int):
        self.post_id = value

    def set_post_date(self, value: int):
        self.post_date = value

    def set_op(self, value: str):
        self.op = value

    def set_param(self, value: str):
        self.param = value

    def set_rc(self, value: int):
        self.rc = value

    def get_ts(self):
        return self.ts

    def get_req_ts(self):
        return self.req_ts

    def get_cli_input(self):
        return self.cli_input

    def get_cmd(self):
        return self.cmd

    def get_blog(self):
        return self.blog

    def get_station(self):
        return self.station

    def get_frequency(self):
        return self.frequency

    def get_post_id(self):
        return self.post_id

    def get_post_date(self):
        return self.post_date

    def get_op(self):
        return self.op

    def get_param(self):
        return self.param

    def get_rc(self):
        return self.rc

    def clone_msg(self, donor: "GuiMessage"):
        self.set_ts()
        self.set_req_ts(donor.get_ts())
        self.set_cli_input(donor.get_cli_input())
        self.set_cmd(donor.get_cmd())
        self.set_blog(donor.get_blog())
        self.set_station(donor.get_station())
        self.set_frequency(donor.get_frequency())
        self.set_post_id(donor.get_post_id())
        self.set_post_date(donor.get_post_date())
        self.set_op(donor.get_op())
        self.set_param(donor.get_param())
        self.set_rc(donor.get_rc())


class CommsMessage:
    msg = {'ts': 0.0, 'req_ts': 0.0, 'direction': '', 'source': "", 'destination': "", 'frequency': 0,
           'offset': 0, 'snr': 0, 'typ': "", 'target': '', 'obj': "", 'payload': "", 'rc': 0}

    # Although the following refers to Js8Call, we need to keep this abstract enough such
    # that another transport mechanism could be used.
    # direction - tx to Js8Call, rx from Js8Call
    # source - call id of the source of this message
    # destination - call id of the destination this message; may be our callid or another
    # frequency - the dial frequency that a message was received on
    # snr - the signal-to-noise ratio for any received messages
    # typ - control, mb_req, mb_rsp, mb_notify
    # target:obj -
    #   * mb_server:service - mb_req
    #   * mb_client:receiver - mb_rsp and mb_notify
    #   * set:radio_frequency - control request
    #   * set:offset - control request
    #   * set:exit - control request
    #   * status:radio_frequency - control notification
    #   * status:offset - control notification
    #   * status:callsign - control notification
    #   * ui_header:tx_led - control notification
    #   * ui_header:rx_led - control notification

    def set_ts(self, ts: float):
        self.msg['ts'] = ts

    def set_req_ts(self, ts: float):
        self.msg['req_ts'] = ts

    def set_direction(self, direction: str):
        self.msg['direction'] = direction

    def set_source(self, source: str):
        self.msg['source'] = source

    def set_destination(self, destination: str):
        self.msg['destination'] = destination

    def set_frequency(self, frequency: int):
        self.msg['frequency'] = frequency

    def set_offset(self, offset: int):
        self.msg['offset'] = offset

    def set_snr(self, snr: int):
        self.msg['snr'] = snr

    def set_blog(self, blog: str):
        self.msg['blog'] = blog

    def set_typ(self, typ: str):
        self.msg['typ'] = typ

    def set_target(self, target: str):
        self.msg['target'] = target

    def set_obj(self, obj: str):
        self.msg['obj'] = obj

    def set_payload(self, payload: [str, int]):
        self.msg['payload'] = payload

    def set_rc(self, rc: int):
        self.msg['rc'] = rc

    def get_ts(self) -> float:
        return self.msg['ts']

    def get_req_ts(self) -> float:
        return self.msg['req_ts']

    def get_direction(self) -> str:
        return self.msg['direction']

    def get_source(self) -> str:
        return self.msg['source']

    def get_destination(self) -> str:
        return self.msg['destination']

    def get_frequency(self) -> int:
        return self.msg['frequency']

    def get_offset(self) -> int:
        return self.msg['offset']

    def get_snr(self) -> int:
        return self.msg['snr']

    def get_blog(self) -> str:
        return self.msg['blog']

    def get_typ(self) -> str:
        return self.msg['typ']

    def get_target(self) -> str:
        return self.msg['target']

    def get_obj(self) -> str:
        return self.msg['obj']

    def get_payload(self) -> str:
        return self.msg['payload']

    def get_rc(self) -> int:
        return self.msg['rc']
