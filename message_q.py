from __future__ import annotations
from enum import Enum


class UiArea(str, Enum):
    HEADER = "header"
    BLOG_LIST = "blog_list"
    BLOG_INFO = "blog_info"
    POST_LIST = "post_list"
    POST_CONTENT = "post_content"
    PROGRESS = "progress"


class MessageTarget(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    COMMS = "comms"
    NONE = "none"  # A value has not yet been assigned


class MessageType(str, Enum):
    REQ = "mb_req"
    CONTROL = "control"
    MB_MSG = "mb_msg"
    SIGNAL = "signal"
    NONE = "none"  # A value has not yet been assigned


class MessageVerb(str, Enum):
    # To FRONTEND - SIGNAL
    FLASH_RX_START = "flash_rx_start"
    FLASH_RX_STOP = "flash_rx_stop"
    FLASH_TX_START = "flash_tx_start"
    FLASH_TX_STOP = "flash_tx_stop"
    SCAN_IND_OFF = "scan_ind_off"
    RELOAD_HEADER = "reload_header"
    RELOAD_BLOG_LIST = "reload_blog_list"
    RELOAD_BLOG_INFO = "reload_blog_info"
    RELOAD_POST_LIST = "reload_post_list"
    RELOAD_POST_CONTENT = "reload_post_content"
    RELOAD_PROGRESS = "reload_progress"

    # To BACKEND - REQ
    FETCH_LISTING = "fetch_listing"
    GET_LISTING = "get_listing"
    FETCH_POST = "fetch_post"
    GET_POST = "get_post"
    GET_BLOG_INFO = "get_blog_info"
    GET_WEATHER = "get_weather"

    # To BACKEND - CONTROL
    SCAN = "scan"
    CHG_FREQ = "chg_freq"
    CHG_BLOG = "chg_blog"
    SHUTDOWN = "shutdown"

    # To BACKEND - MB_MSG
    INFORM = "inform"
    ANNOUNCE = "announce"

    # To BACKEND - SIGNAL
    NOTE_FREQ = "note_freq"
    NOTE_OFFSET = "note_offset"
    NOTE_CALLSIGN = "note_callsign"

    # To COMMS - MB_MSG
    SEND = "send"

    # To COMMS - CONTROL
    SET_FREQ = "set_freq"
    GET_FREQ = "get_freq"
    GET_OFFSET = "get_offset"
    GET_CALLSIGN = "get_callsign"
    NO_OP = "no_op"
    # SHUTDOWN = "shutdown"

    NONE = "none"  # A value has not yet been assigned


class MessageOperator(str, Enum):
    NULL = ''
    EQ = 'eq'
    GT = 'gt'
    LT = 'lt'
    LATEST = 'latest'
    RECENT = 'recent'
    MORE = 'more'
    NONE = "none"  # A value has not yet been assigned


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
        "param",
    )

    def __init__(self, **kwargs):
        # Defaults
        self.target: MessageTarget = MessageTarget.NONE
        self.typ: MessageType = MessageType.NONE
        self.verb: MessageVerb = MessageVerb.NONE
        self.operator: MessageOperator = MessageOperator.NONE
        self.source: str = ""
        self.destination: str = ""
        self.param: str = ""

        if kwargs:
            self.set_many(**kwargs)

    # ---- efficiency helpers ----
    def set_many(self, **kwargs):
        """Bulk-assign fields in one Python call.

        Example:
            m.set_many(target=MessageTarget.BACKEND, typ=MessageType.MB_MSG, verb=MessageVerb.INFORM ...)
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

    def get_param(self):
        return self.param
