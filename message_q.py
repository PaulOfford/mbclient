from __future__ import annotations
import time
from enum import Enum


class MessageTarget(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    COMMS = "comms"


class MessageType(str, Enum):
    REQ = "mb_req"
    CONTROL = "control"
    MB_MSG = "mb_msg"
    SIGNAL = "signal"


class MessageVerb(str, Enum):
    FLASH_RX_START = "flash_rx_start"
    FLASH_RX_STOP = "flash_rx_stop"
    FLASH_TX_START = "flash_tx_start"
    FLASH_TX_STOP = "flash_tx_stop"
    SCAN_OFF = "scan_off"
    RELOAD_HEADER = "reload_header"
    RELOAD_BLOG_LIST = "reload_blog_list"
    RELOAD_BLOG_INFO = "reload_blog_info"
    RELOAD_POST_LIST = "reload_post_list"
    RELOAD_POST_CONTENT = "reload_post_content"
    RELOAD_PROGRESS = "reload_progress"
    FETCH_LISTING = "fetch_listing"
    GET_LISTING = "get_listing"
    FETCH_POST = "fetch_post"
    GET_POST = "get_postr"
    CHG_FREQ = "chg_freq"
    CHG_BLOG_FREQ = "chg_blog_freq"
    SHUTDOWN = "shutdown"
    INFORM = "inform"
    ANNOUNCE = "announce"
    NOTE_FREQ = "note_freq"
    NOTE_OFFSET = "note_offset"
    NOTE_CALLSIGN = "note_callsign"
    SEND = "send"
    SET_FREQ = "set_freq"
    GET_FREQ = "get_freq"
    GET_OFFSET = "get_offset"
    GET_CALLSIGN = "get_callsign"
    NO_OP = "no_op"


class MessageOperator(str, Enum):
    NULL = ''
    EQ = 'eq'
    GT = 'gt'
    LT = 'lt'
    LATEST = 'latest'
    RECENT = 'recent'
    MORE = 'more'

    # ToDo: This following to be moved in the new message architecture
    RELOAD = 'reload'
    FLASH_RX_START = 'flash_rx_start'
    FLASH_RX_STOP = 'flash_rx_stop'
    PTT_ON = 'ptt_on'
    PTT_OFF = 'ptt_off'


class GuiMessage:
    """Message sent between GUI and backend.

    NOTE: This class historically used class attributes for defaults; we now
    initialise instance state in __init__ to avoid accidental shared state.
    """

    __slots__ = (
        "ts",
        "req_ts",
        "cli_input",
        "cmd",
        "blog",
        "station",
        "frequency",
        "post_id",
        "post_date",
        "verb",
        "op",
        "param",
        "rc",
    )

    def __init__(self):
        self.ts = 0.0
        self.req_ts = 0.0
        self.cli_input = ""
        self.cmd = ""
        self.blog = ""
        self.station = ""
        self.frequency = 0
        self.post_id = 0
        self.post_date = 0
        self.verb = None
        self.op = None
        self.param = ""
        self.rc = 0

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

    def set_op(self, value: MessageOperator):
        self.op = value

    def set_param(self, value: str):
        self.param = value

    def set_rc(self, value: int):
        self.rc = value

    def get_ts(self) -> float:
        return self.ts

    def get_req_ts(self) -> float:
        return self.req_ts

    def get_cli_input(self) -> str:
        return self.cli_input

    def get_cmd(self) -> str:
        return self.cmd

    def get_blog(self) -> str:
        return self.blog

    def get_station(self) -> str:
        return self.station

    def get_frequency(self) -> int:
        return self.frequency

    def get_post_id(self) -> int:
        return self.post_id

    def get_post_date(self) -> int:
        return self.post_date

    def get_op(self) -> MessageOperator:
        return self.op

    def get_param(self) -> str:
        return self.param

    def get_rc(self) -> int:
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


class UnifiedMessage:
    """Message used for transport to/from the comms layer.

    Efficiency improvements:
      - Uses __slots__ to reduce per-instance overhead.
      - Initialises instance state in __init__ (avoids accidental shared state).
      - Provides set_many() to avoid many Python-level setter calls.
      - Provides small factory constructors for common message shapes.
    """

    __slots__ = (
        "target",
        "typ",
        "verb",
        "operator",
        "value",
        "source",
        "destination",
        "frequency",
        "param",
    )

    def __init__(self, **kwargs):
        # Defaults
        self.target: MessageTarget = None
        self.typ: MessageType = None
        self.verb: MessageVerb = None
        self.operator: MessageOperator = None
        self.source: str = ""
        self.destination: str = ""
        self.frequency: int = 0
        self.param: str = ""

        if kwargs:
            self.set_many(**kwargs)

    # ---- efficiency helpers ----
    def set_many(self, **kwargs):
        """Bulk-assign fields in one Python call.

        Example:
            m.set_many(target=MessageTarget.BACKEND, type=MessageType.MB_MSG, verb=MessageVerb.INFORM ...)
        """
        for k, v in kwargs.items():
            setattr(self, k, v)

    # Getters

    def get_target(self) -> MessageTarget:
        return self.target

    def get_typ(self) -> MessageType:
        return self.typ

    def get_verb(self) -> MessageVerb:
        return self.verb

    def get_operator(self) -> MessageOperator:
        return self.operator

    def get_source(self) -> str:
        """Get the callsign of the station that sent the message.
        """
        return self.source

    def get_destination(self) -> str:
        """Get the callsign of the station that the message is going to.
            The destination can also be @MB for announcements.
        """
        return self.destination

    def get_param(self) -> str:
        return self.param
