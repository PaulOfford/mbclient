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
    REQUEST = "request"
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
    RELOAD_UI = "reload_ui"

    # To BACKEND - REQ
    FETCH_LISTING = "fetch_listing"
    GET_LISTING = "get_listing"
    FETCH_POST = "fetch_post"
    GET_POST = "get_post"
    GET_BLOG_INFO = "get_blog_info"
    GET_WEATHER = "get_weather"

    # To BACKEND - CONTROL
    SCAN = "scan"
    CHG_RADIO_FREQUENCY = "chg_radio_frequency"
    CHG_USER_FREQUENCY = "chg_user_frequency"
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
    MORE = 'more'
    NONE = "none"  # A value has not yet been assigned


class MessageParameter(str, Enum):
    SOURCE = 'source'  # The callsign of the station that sent the message.
    DESTINATION = 'destination'  # The callsign of the station that the message is going or @MB for announcements.
    CALLSIGN = 'callsign'  # The callsign of the station that is running this software
    FREQUENCY = 'frequency'
    OFFSET = 'offset'
    BLOG = 'blog'
    POST_ID = 'post_id'
    MB_MSG = 'mb_msg'
    UI_AREA = 'ui_area'
    OPERATOR = 'operator'


class UnifiedMessage:
    """Message used for transport to/from the comms layer.

    Efficiency improvements:
      - Uses __slots__ to reduce per-instance overhead.
      - Initialises instance state in __init__ (avoids accidental shared state).
      - Provides set_many() to avoid many Python-level setter calls.
      - Provides small factory constructors for common message shapes.
    """

    __slots__ = (
        "ts",
        "priority",
        "target",
        "typ",
        "verb",
        "params",
    )

    def __init__(self, **kwargs):
        # Defaults
        self.ts: float = 0
        self.priority: int = 1
        self.target: MessageTarget = MessageTarget.NONE
        self.typ: MessageType = MessageType.NONE
        self.verb: MessageVerb = MessageVerb.NONE
        self.params: {} = {}

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

    def get_ts(self) -> float:
        return self.ts

    def get_priority(self) -> int:
        return self.priority

    def get_target(self) -> MessageTarget:
        return self.target

    def get_typ(self) -> MessageType:
        return self.typ

    def get_verb(self) -> MessageVerb:
        return self.verb

    def get_param(self, parameter: MessageParameter):
        return self.params[parameter.value]

    def get_params(self) -> {}:
        return self.params
