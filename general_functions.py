import time
import logging

from db_table import DbTable
from message_q import b2f_q, UnifiedMessage, MessageTarget, MessageType, MessageVerb, MessageParameter, UiArea

logger = logging.getLogger(__name__)


def reload_ui_areas(ui_area: str):
    m = UnifiedMessage()

    m.set_many(
        target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL,
        verb=MessageVerb.RELOAD_UI,
        params={MessageParameter.UI_AREA: ui_area}
    )

    logger.info(
        f"Sending to FRONTEND: {m.get_target()}|{m.get_typ()}|{m.get_verb()}|{m.get_params()}"
    )
    b2f_q.put(m)

    return


def add_progress_txt(progress_msg: str):
    progress_table = DbTable('progress')

    progress_table.insert(
        row={
            'qso_date': time.time(),
            'blog': '',
            'station': '',
            'frequency': 0,
            'offset': 0,
            'message': progress_msg
        }
    )

    reload_ui_areas(UiArea.PROGRESS)

    return


def add_progress_m(m: UnifiedMessage):

    progress_msg = f"To: {m.get_target()} Req: {m.get_verb()}"

    if m.get_verb() == MessageVerb.GET_POST or m.get_verb() == MessageVerb.FETCH_POST\
            or m.get_verb() == MessageVerb.GET_LISTING or m.get_verb() == MessageVerb.FETCH_LISTING:
        try:
            progress_msg += f" {m.get_param(MessageParameter.POST_ID)}"
        except KeyError:
            pass

    if m.get_verb() == MessageVerb.CHG_BLOG:
        progress_msg += f" {m.get_param(MessageParameter.BLOG)}"

    if m.get_verb() == MessageVerb.CHG_BLOG or m.get_verb() == MessageVerb.CHG_USER_FREQUENCY or \
            m.get_verb() == MessageVerb.CHG_RADIO_FREQUENCY:
        try:
            progress_msg += f" {m.get_param(MessageParameter.FREQUENCY)}"
        except KeyError:
            pass

    if m.get_verb() == MessageVerb.INFORM:
        try:
            progress_msg += f" {m.get_param(MessageParameter.MB_MSG)}"
        except KeyError:
            pass

    if m.get_verb() == MessageVerb.ANNOUNCE:
        try:
            progress_msg += f" {m.get_param(MessageParameter.MB_MSG)}"
        except KeyError:
            pass

    if m.get_target() == MessageTarget.COMMS:
        try:
            progress_msg += f" {m.get_param(MessageParameter.MB_MSG)}"
        except KeyError:
            pass

    progress_table = DbTable('progress')

    progress_table.insert(
        row={
            'qso_date': time.time(),
            'blog': '',
            'station': '',
            'frequency': 0,
            'offset': 0,
            'message': progress_msg
        }
    )

    reload_ui_areas(UiArea.PROGRESS)

    return
