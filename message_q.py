from __future__ import annotations
import time
from enum import Enum


class MessageType(str, Enum):
    CONTROL = "control"
    MB_REQ = "mb_req"
    MB_RSP = "mb_rsp"
    MB_NOTIFY = "mb_notify"
    SIGNAL = "signal"


class MessageTarget(str, Enum):
    SET = "set"
    STATUS = "status"
    MB_SERVICE = "mb_service"
    MB_CLIENT = "mb_client"
    FRONTEND = "frontend"


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
        self.op = MessageOperator.NULL
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


class CommsMessage:
    """Message used for transport to/from the comms layer.

    Efficiency improvements:
      - Uses __slots__ to reduce per-instance overhead.
      - Initialises instance state in __init__ (avoids accidental shared state).
      - Provides set_many() to avoid many Python-level setter calls.
      - Provides small factory constructors for common message shapes.
    """

    __slots__ = (
        "ts",
        "req_ts",
        "direction",
        "blog",
        "source",
        "destination",
        "frequency",
        "offset",
        "snr",
        "typ",
        "target",
        "obj",
        "payload",
        "rc",
    )

    def __init__(self, **kwargs):
        # Defaults
        self.ts = 0.0
        self.req_ts = 0.0
        self.direction = ""
        self.blog = ""
        self.source = ""
        self.destination = ""
        self.frequency = 0
        self.offset = 0
        self.snr = 0
        self.typ = ""
        self.target = ""
        self.obj = ""
        self.payload = ""
        self.rc = 0

        if kwargs:
            self.set_many(**kwargs)

    # ---- efficiency helpers ----
    def set_many(self, **kwargs):
        """Bulk-assign fields in one Python call.

        Example:
            m.set_many(ts=..., direction='rx', typ='control', target='status', obj='offset', payload='123')
        """
        for k, v in kwargs.items():
            setattr(self, k, v)

    # ---- factories for common message shapes ----
    @classmethod
    def signal_frontend(cls, ts: float, obj: str, payload: str) -> "CommsMessage":
        return cls(
            ts=ts,
            direction="rx",
            typ=MessageType.SIGNAL,
            target=MessageTarget.FRONTEND,
            obj=obj,
            payload=payload,
        )

    @classmethod
    def control_status(
        cls, ts: float, obj: str, payload: str, *, frequency: int = 0, offset: int = 0
    ) -> "CommsMessage":
        return cls(
            ts=ts,
            direction="rx",
            typ=MessageType.CONTROL,
            target=MessageTarget.STATUS,
            obj=obj,
            payload=payload,
            frequency=frequency,
            offset=offset,
        )

    @classmethod
    def control_set(cls, ts: float, obj: str, payload: str) -> "CommsMessage":
        return cls(
            ts=ts,
            direction="tx",
            typ=MessageType.CONTROL,
            target=MessageTarget.SET,
            obj=obj,
            payload=payload,
        )

    @classmethod
    def mb_rx(
        cls,
        ts: float,
        source: str,
        destination: str,
        *,
        frequency: int,
        snr: int,
        typ: str,
        payload: str,
    ) -> "CommsMessage":
        return cls(
            ts=ts,
            direction="rx",
            source=source,
            destination=destination,
            frequency=frequency,
            snr=snr,
            typ=typ,
            target=MessageTarget.MB_CLIENT,
            obj="receiver",
            payload=payload,
        )

    # ---- existing setters/getters (kept for compatibility) ----
    def set_ts(self, ts: float):
        self.ts = ts

    def set_req_ts(self, ts: float):
        self.req_ts = ts

    def set_direction(self, direction: str):
        self.direction = direction

    def set_source(self, source: str):
        self.source = source

    def set_destination(self, destination: str):
        self.destination = destination

    def set_frequency(self, frequency: int):
        self.frequency = frequency

    def set_offset(self, offset: int):
        self.offset = offset

    def set_snr(self, snr: int):
        self.snr = snr

    def set_blog(self, blog: str):
        self.blog = blog

    def set_typ(self, typ: str):
        self.typ = typ

    def set_target(self, target: str):
        self.target = target

    def set_obj(self, obj: str):
        self.obj = obj

    def set_payload(self, payload: str):
        self.payload = payload

    def set_rc(self, rc: int):
        self.rc = rc

    def get_ts(self) -> float:
        return self.ts

    def get_req_ts(self) -> float:
        return self.req_ts

    def get_direction(self) -> str:
        return self.direction

    def get_source(self) -> str:
        return self.source

    def get_destination(self) -> str:
        return self.destination

    def get_frequency(self) -> int:
        return self.frequency

    def get_offset(self) -> int:
        return self.offset

    def get_snr(self) -> int:
        return self.snr

    def get_blog(self) -> str:
        return self.blog

    def get_typ(self) -> str:
        return self.typ

    def get_target(self) -> str:
        return self.target

    def get_obj(self) -> str:
        return self.obj

    def get_payload(self) -> str:
        return self.payload

    def get_rc(self) -> int:
        return self.rc
