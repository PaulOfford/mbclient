import time
import queue
import re
import logging

from mbclient.status import Status
from mbclient.settings import Settings
from mbclient.message_q import f2b_q, b2f_q, b2c_q_p0, b2c_q_p1, c2b_q, UiArea, UnifiedMessage, MessageTarget,\
    MessageType, MessageVerb, MessageOperator, MessageParameter
from mbclient.db_table import DbTable
from mbclient.general_functions import add_progress_m, reload_ui_areas

from .config import SETTINGS

logger = logging.getLogger(__name__)


def compress_date(post_epoch: int) -> str:
    if post_epoch > 0:
        dt_string = time.strftime('%Y-%m-%d', time.gmtime(post_epoch))
        year = dt_string[2:4]
        day = dt_string[8:10]
        if dt_string[5:7] == '10':
            month = 'A'
        elif dt_string[5:7] == '11':
            month = 'B'
        elif dt_string[5:7] == '12':
            month = 'C'
        else:
            month = dt_string[6:7]
        return year + month + day
    else:
        return ''


def signal_frontend(verb: MessageVerb):
    m = UnifiedMessage.create(
        priority=0,
        target='FRONTEND',
        typ='SIGNAL',
        verb=verb
    )
    b2f_q.put(m)


class BlogInstance:
    latest_post_id: int = None
    latest_post_date: int = None
    last_seen: int = None
    selected: int = None
    blog_field = [
        'blog', 'frequency', 'snr', 'latest_post_id', 'latest_post_date', 'last_seen_date', 'is_selected'
    ]

    def __init__(self, name: str, freq: int):
        blog_table = DbTable('blog')
        results = blog_table.select(where=f"blog='{name}' AND frequency={freq}", limit=1, hdr_list=self.blog_field)
        if len(results) > 0:
            result = results[0]
            self.snr = result['snr']
            self.latest_post_id = result['latest_post_id']
            self.latest_post_date = result['latest_post_date']
            self.last_seen = result['last_seen_date']
            self.selected = result['is_selected']
        return

    def get_latest_post_details(self):
        return self.latest_post_id, self.latest_post_date

    def get_last_seen(self) -> int:
        return self.last_seen

    def is_selected(self) -> bool:
        if self.selected > 0:
            return True
        else:
            return False


class ServerMsgProcessors:
    listing_extractor = '^([+-])([EL])([\\d,]*)~\\n*([\\S\\s]+)'
    post_extractor = '^([+-])(G)(\\d+)~\\n*([\\S\\s]+)'
    weather_extractor = '^([+-])(WX)~\\n*([\\S\\s]+)'
    info_extractor = '^([+-])(I)~\\n*([\\S\\s]+)'
    announce_extractor = '^(\\d+) +(\\d{6})'
    announce_extractor_old = '^([A-Z,0-9/]+) +(\\d+) +(\\d{4}-\\d{2}-\\d{2})'

    is_connected: bool = True

    def __init__(self):
        pass

    @staticmethod
    def signal_reload(ui_area):
        reload_ui_areas(ui_area)

    def process_inform(self, m: UnifiedMessage):
        status = Status()
        inform_patterns = [self.listing_extractor, self.post_extractor, self.weather_extractor, self.info_extractor]
        for reg_ex in inform_patterns:
            result = re.findall(reg_ex, m.get_param(MessageParameter.MB_MSG))
            if len(result) == 0:
                continue
            else:
                result = list(result[0])
                if result[0] == '+':
                    mb_cmd = result[1]
                    if mb_cmd == 'G':
                        self.process_post(
                            destination=m.get_param(MessageParameter.DESTINATION),
                            blog=m.get_param(MessageParameter.SOURCE),
                            post_id=result[2],
                            body=result[3]
                        )
                        self.signal_reload(UiArea.POST_CONTENT)
                    elif mb_cmd == 'E' or mb_cmd == 'L':
                        destination, cmd, blog, post_range, lines = self.parse_listing(m)
                        self.process_listing(
                            destination=destination,
                            cmd=cmd, blog=blog,
                            post_range=post_range,
                            lines=lines
                        )
                        self.signal_reload(UiArea.POST_LIST)
                    elif mb_cmd == 'I':
                        self.process_info(
                            blog=m.get_param(MessageParameter.SOURCE),
                            frequency=status.radio_frequency,
                            blog_info=result[2]
                        )
                        self.signal_reload(UiArea.BLOG_INFO)
                break
        return

    def process_announcement(self, m: UnifiedMessage) -> None:
        announcement_patterns = [self.announce_extractor, self.announce_extractor_old]
        for entry in announcement_patterns:
            result = re.findall(entry, m.get_param(MessageParameter.MB_MSG))
            if len(result) > 0:
                is_valid = False
                post_id = 0
                post_date = 0
                result = list(result[0])
                if len(result) == 2:
                    post_id = int(result[0])
                    post_date = time.mktime(time.strptime(result[1] + ' GMT', '%y%m%d %Z'))
                    is_valid = True
                elif len(result) == 3:
                    post_id = int(result[1])
                    post_date = time.mktime(time.strptime(result[2] + ' GMT', '%Y-%m-%d %Z'))
                    is_valid = True
                if is_valid:
                    self.update_blog_list(
                        blog=m.get_param(MessageParameter.SOURCE),
                        post_id=post_id,
                        post_date=post_date
                    )
                    self.signal_reload(UiArea.BLOG_LIST)
        return

    def process_listing(self, destination: str, cmd: str, blog: str, post_range: str, lines: list[dict]):
        status = Status()
        post_table = DbTable('post')
        qso_date = time.time()
        for line in lines:
            db_values = post_table.select(
                where=f"blog='{blog}' AND post_id={line['post_id']}", hdr_list=['body', 'is_selected']
            )
            if len(db_values) == 0:
                post_table.delete(where=f"blog='{blog}' AND post_id={line['post_id']}")
                row = {
                    'qso_date': qso_date, 'blog': blog,
                    'directed_to': destination, 'frequency': status.radio_frequency,
                    'offset': status.offset, 'cmd': cmd + post_range, 'post_id': line['post_id'],
                    'post_date': line['post_date'], 'title': line['title'], 'body': '', 'is_selected': 0
                }
                post_table.insert(row)
            elif destination == status.callsign:
                post_table.delete(where=f"blog='{blog}' AND post_id={line['post_id']}")
                row = {
                    'qso_date': qso_date, 'blog': blog, 'directed_to': destination,
                    'frequency': status.radio_frequency, 'offset': status.offset, 'cmd': cmd,
                    'post_id': line['post_id'], 'post_date': line['post_date'], 'title': line['title'],
                    'body': db_values[0]['body'], 'is_selected': db_values[0]['is_selected']
                }
                post_table.insert(row)
            self.update_blog_list(blog, line['post_id'], line['post_date'])
        self.signal_reload(UiArea.POST_LIST)
        self.signal_reload(UiArea.POST_CONTENT)

    @staticmethod
    def process_post(destination: str, blog: str, post_id: int, body: str):
        status = Status()
        post_table = DbTable('post')
        db_values = post_table.select(where=f"blog='{blog}' AND post_id={post_id}", limit=1, hdr_list=['post_id'])
        if len(db_values) > 0:
            post_table.update(value_dictionary={'body': body}, where=f"blog='{blog}' AND post_id={post_id}")
            reload_ui_areas(UiArea.POST_CONTENT)
        else:
            post_table.insert(
                row={
                    'qso_date': 0, 'blog': blog, 'directed_to': destination,
                    'frequency': status.radio_frequency, 'offset': status.offset, 'cmd': 'G',
                    'post_id': post_id, 'post_date': 0.0, 'title': f'** {body[:20]}', 'body': body, 'is_selected': 0
                }
            )
            reload_ui_areas(UiArea.POST_LIST)

    def process_weather(self, m: UnifiedMessage):
        pass

    @staticmethod
    def process_info(blog: str, frequency: int, blog_info: str):
        blog_table = DbTable('blog')
        blog_table.update(value_dictionary={'info': blog_info}, where=f"blog='{blog}' AND frequency={frequency}")
        reload_ui_areas(UiArea.BLOG_INFO)

    def parse_listing(self, m: UnifiedMessage) -> tuple[str, str, str, str, list[dict]]:
        result = re.findall(self.listing_extractor, m.get_param(MessageParameter.MB_MSG))
        result = list(result[0])
        cmd: str = result[1]
        post_range: str = result[2]
        body: str = result[3]
        entries: list[dict] = []
        lines = body.split('\n')
        for line in lines:
            stripped_line = line.strip()
            if len(stripped_line) == 0:
                continue
            if stripped_line == 'NO POSTS FOUND':
                entries.append({'post_id': -1, 'post_date': 0, 'title': 'NO POSTS FOUND'})
                break
            if cmd == 'E':
                details = re.findall('(\\d+) - (\\d{4}-\\d{2}-\\d{2}) - ([\\S\\s]+)', stripped_line)
                if len(details) > 0:
                    post_id = int(details[0][0])
                    post_date = time.mktime(time.strptime(details[0][1], '%Y-%m-%d'))
                    title = details[0][2]
                    entries.append({'post_id': post_id, 'post_date': post_date, 'title': title})
                else:
                    logger.info(f'Received extended listing is too corrupt to interpret: {line}')
                    continue
            else:
                details = re.findall('(\\d+) - ([\\S\\s]+)', line)
                if len(details[0]) > 0:
                    post_id = int(details[0][0])
                    post_date = 0
                    title = details[0][1]
                    entries.append({'post_id': post_id, 'post_date': post_date, 'title': title})
                else:
                    logger.info(f'Received listing is too corrupt to interpret: {line}')
                    continue
        return m.get_param(MessageParameter.DESTINATION), cmd, m.get_param(MessageParameter.SOURCE), post_range, entries

    def update_blog_list(self, blog: str, post_id: int, post_date: int) -> None:
        status = Status()
        blog_table = DbTable('blog')
        results = blog_table.select(
            where=f"blog='{blog}' AND frequency={status.radio_frequency}",
            limit=1, hdr_list=['latest_post_id', 'latest_post_date']
        )
        if len(results) > 0:
            latest_post_id = results[0]['latest_post_id']
            if post_id >= latest_post_id:
                blog_table.update(
                    value_dictionary={
                        'latest_post_id': post_id, 'latest_post_date': post_date, 'last_seen_date': time.time()
                    },
                    where=f"blog='{blog}' AND frequency={status.radio_frequency}"
                )
            else:
                blog_table.update(
                    value_dictionary={
                        'last_seen_date': time.time()
                    },
                    where=f"blog='{blog}' AND frequency={status.radio_frequency}"
                )
        else:
            default_info = "To get Blog Information, right click on the blog list entry and choose Get info."
            blog_table.insert(
                row={
                    'blog': blog, 'frequency': status.radio_frequency, 'snr': 0,
                    'latest_post_id': post_id, 'latest_post_date': post_date, 'last_seen_date': time.time(),
                    'info': default_info, 'is_selected': 0
                }
            )
        self.signal_reload(UiArea.BLOG_LIST)

    def process_note_callsign(self, m: UnifiedMessage):
        status = Status()
        status.set_callsign(m.get_param(MessageParameter.CALLSIGN))
        self.signal_reload(UiArea.HEADER)

    def process_note_freq(self, m: UnifiedMessage):
        status = Status()
        status.set_radio_frequency(m.get_param(MessageParameter.FREQUENCY))
        self.signal_reload(UiArea.HEADER)

    def process_note_offset(self, m: UnifiedMessage):
        status = Status()
        status.set_offset(m.get_param(MessageParameter.OFFSET))
        self.signal_reload(UiArea.HEADER)

    @staticmethod
    def process_note_ptt(m: UnifiedMessage):
        if m.get_param(MessageParameter.PTT):
            verb = MessageVerb.FLASH_TX_START
        else:
            verb = MessageVerb.FLASH_TX_STOP
        signal_frontend(verb)

    @staticmethod
    def process_note_rx(m: UnifiedMessage):
        if m.get_param(MessageParameter.RX):
            verb = MessageVerb.FLASH_RX_START
        else:
            verb = MessageVerb.FLASH_RX_STOP
        signal_frontend(verb)

    def process_note_disconnect(self):
        self.is_connected = False
        verb = MessageVerb.NOTE_DISCONNECT
        signal_frontend(verb)

    def process_rx_message(self, m: UnifiedMessage):
        if m.get_typ() == MessageType.MB_MSG:
            mb_cmd = str(m.get_param(MessageParameter.MB_MSG)).split('\n')[0]
            logger.info(
                f"RECV <- {m.get_param(MessageParameter.SOURCE)}: {mb_cmd}"
            )
            if m.get_verb() == MessageVerb.INFORM:
                self.process_inform(m)
            elif m.get_verb() == MessageVerb.ANNOUNCE:
                self.process_announcement(m)

        elif m.get_typ() == MessageType.SIGNAL:
            if m.get_verb() == MessageVerb.NOTE_CALLSIGN:
                self.process_note_callsign(m)
            elif m.get_verb() == MessageVerb.NOTE_FREQ:
                self.process_note_freq(m)
            elif m.get_verb() == MessageVerb.NOTE_OFFSET:
                self.process_note_offset(m)
            elif m.get_verb() == MessageVerb.NOTE_PTT:
                self.process_note_ptt(m)
            elif m.get_verb() == MessageVerb.NOTE_RX:
                self.process_note_rx(m)
            elif m.get_verb() == MessageVerb.NOTE_DISCONNECT:
                self.process_note_disconnect()


class BeProcessor:
    post_fields = [
        'qso_date', 'blog', 'directed_to', 'frequency', 'offset',
        'cmd', 'post_id', 'post_date', 'title', 'body'
    ]

    processor = ServerMsgProcessors()

    def __init__(self):
        pass

    def listing_is_in_cache(self, blog, post_id) -> bool:
        where_clause = f"blog='{blog}'"
        where_clause += f' AND post_id={post_id}'
        where_clause += " AND title<>'' and post_date>0"
        post_table = DbTable('post')
        db_values = post_table.select(
            where=where_clause, group_by='post_id', order_by='post_id, body, title', desc=True,
            hdr_list=self.post_fields
        )
        return len(db_values) > 0

    @staticmethod
    def get_post_id_list(m: UnifiedMessage):
        settings = Settings()
        post_list = []
        if m.get_param(MessageParameter.OPERATOR) == MessageOperator.EQ:
            post_id = m.get_param(MessageParameter.POST_ID)
            post_list.append(post_id)
        elif m.get_param(MessageParameter.OPERATOR) == MessageOperator.LATEST:
            pass
        elif m.get_param(MessageParameter.OPERATOR) == MessageOperator.MORE:
            post_id = m.get_param(MessageParameter.POST_ID)
            starting_post_id = max(int(post_id) - settings.max_listing, 1)
            for i in range(starting_post_id, int(post_id)):
                post_list.append(i)
        return post_list

    @staticmethod
    def get_listing_command(post_id_list: list[int]) -> str:
        if len(post_id_list) > 0:
            post_list_string = ','.join(map(str, post_id_list))
        else:
            post_list_string = ''
        mb_cmd = f'E{post_list_string}~'
        return mb_cmd

    def verb_fetch_listing(self, m: UnifiedMessage):
        blog = m.get_param(MessageParameter.DESTINATION)
        post_id_list = self.get_post_id_list(m)
        if len(post_id_list) == 0:
            return
        svr_request_list = []
        for post_id in post_id_list:
            if self.listing_is_in_cache(blog, post_id):
                continue
            else:
                svr_request_list.append(post_id)
        if len(svr_request_list) == 0:
            return
        self.mb_msg_send(
            destination=m.get_param(MessageParameter.DESTINATION),
            mb_cmd=self.get_listing_command(svr_request_list)
        )
        return

    def verb_get_listing(self, m: UnifiedMessage):
        if m.get_param(MessageParameter.OPERATOR) == MessageOperator.LATEST:
            mb_cmd = 'E~'
        else:
            mb_cmd = self.get_listing_command(post_id_list=self.get_post_id_list(m))
        self.mb_msg_send(destination=m.get_param(MessageParameter.DESTINATION), mb_cmd=mb_cmd)
        return

    @staticmethod
    def verb_fetch_post(m: UnifiedMessage) -> None:
        blog = m.get_param(MessageParameter.DESTINATION)
        post_id = int(m.get_param(MessageParameter.POST_ID))
        post_table = DbTable('post')
        post_table.update(where=f"blog='{blog}'", value_dictionary={'is_selected': 0})
        post_table.update(where=f"blog='{blog}' AND post_id={post_id}", value_dictionary={'is_selected': 1})
        return

    def verb_get_post(self, m: UnifiedMessage) -> None:
        mb_cmd = f'G{m.get_param(MessageParameter.POST_ID)}~'
        self.mb_msg_send(destination=m.get_param(MessageParameter.DESTINATION), mb_cmd=mb_cmd)
        return

    def verb_get_weather(self, m: UnifiedMessage) -> None:
        self.mb_msg_send(destination=m.get_param(MessageParameter.DESTINATION), mb_cmd='WX~')
        return

    def verb_get_blog_info(self, m: UnifiedMessage) -> None:
        logger.debug('comms: send: I~')
        self.mb_msg_send(destination=m.get_param(MessageParameter.DESTINATION), mb_cmd='I~')
        return

    def verb_scan(self, m: UnifiedMessage) -> None:
        self.mb_msg_send(destination=m.get_param(MessageParameter.DESTINATION), mb_cmd='Q')
        return

    @staticmethod
    def set_hdr_freq(frequency: int):
        s = DbTable('status')
        s.update(where=None, value_dictionary={'radio_frequency': frequency, 'user_frequency': frequency})
        reload_ui_areas(UiArea.HEADER)

    @staticmethod
    def set_hdr_offset(offset: int):
        s = DbTable('status')
        s.update(where=None, value_dictionary={'offset': offset})
        reload_ui_areas(UiArea.HEADER)

    def set_rig_frequency(self, frequency: int):
        m = UnifiedMessage.create(
            priority=0,
            target='COMMS',
            typ='CONTROL',
            verb='SET_FREQ',
            params={'frequency': frequency}
        )
        self.send_to_comms(m)

    @staticmethod
    def set_hdr_callsign(callsign: str):
        s = DbTable('status')
        s.update(where=None, value_dictionary={'callsign': callsign})
        reload_ui_areas(UiArea.HEADER)

    def mb_msg_send(self, destination: str, mb_cmd: str):
        m = UnifiedMessage.create(
            priority=1,
            target=MessageTarget.COMMS,
            typ=MessageType.MB_MSG,
            verb=MessageVerb.SEND,
            params={MessageParameter.DESTINATION: destination, MessageParameter.MB_MSG: mb_cmd}
        )
        logger.debug(f'Sending to COMMS: {m.get_target()}|{m.get_typ()}|{m.get_verb()}|{m.get_params()}')
        self.send_to_comms(m)
        return

    @staticmethod
    def select_blog(m: UnifiedMessage):
        blog = m.get_param(MessageParameter.BLOG)
        frequency = m.get_param(MessageParameter.FREQUENCY)
        if len(blog) > 0:
            b = DbTable('blog')
            b.update(where=None, value_dictionary={'is_selected': 0})
            b.update(where=f"blog='{blog}' AND frequency={frequency}", value_dictionary={'is_selected': 1})

        reload_ui_areas(UiArea.BLOG_LIST)
        reload_ui_areas(UiArea.BLOG_INFO)

    def verb_chg_blog(self, m: UnifiedMessage) -> None:
        if m.get_verb() == MessageVerb.CHG_BLOG:
            self.select_blog(m)
            reload_ui_areas(UiArea.BLOG_LIST)
            return

    def verb_chg_radio_frequency(self, m: UnifiedMessage) -> None:
        status = Status()
        self.set_rig_frequency(m.get_param(MessageParameter.FREQUENCY))
        reload_ui_areas(UiArea.HEADER)
        status.set_radio_frequency(m.get_param(MessageParameter.FREQUENCY))
        return

    @staticmethod
    def verb_chg_user_frequency(m: UnifiedMessage) -> None:
        status = Status()
        status.set_user_frequency(m.get_param(MessageParameter.FREQUENCY))
        return

    def send_to_comms(self, m: UnifiedMessage):
        if not self.processor.is_connected:
            return  # We've lost comms

        if m.get_param(MessageParameter.MB_MSG):
            log_msg = m.get_param(MessageParameter.MB_MSG).split('\n')[0]
            logger.info(f"SEND -> {m.get_param(MessageParameter.DESTINATION)}: {log_msg}")

        logger.debug(
            f"Sending to COMMS: {m.get_target().value}|{m.get_typ().value}|{m.get_verb().value}|{m.get_params()}")
        if m.priority == 0:
            b2c_q_p0.put(m)
        elif m.priority == 1:
            b2c_q_p1.put(m)

        # If it's not P0 or P1, ignore it.

    def type_process_request(self, m: UnifiedMessage):
        logger.info(
            f"FRONTEND ->:"
            f" {m.get_param(MessageParameter.DESTINATION)}"
            f"|{m.get_verb()}"
            f"|{m.get_param(MessageParameter.OPERATOR)}"
            f"|{m.get_param(MessageParameter.POST_ID)}"
        )
        if m.get_verb() == MessageVerb.FETCH_LISTING:
            add_progress_m(m)
            self.verb_fetch_listing(m)
        elif m.get_verb() == MessageVerb.GET_LISTING:
            add_progress_m(m)
            self.verb_get_listing(m)
        elif m.get_verb() == MessageVerb.FETCH_POST:
            add_progress_m(m)
            self.verb_fetch_post(m)
        elif m.get_verb() == MessageVerb.GET_POST:
            add_progress_m(m)
            self.verb_get_post(m)
        elif m.get_verb() == MessageVerb.SCAN:
            add_progress_m(m)
            self.verb_scan(m)
        elif m.get_verb() == MessageVerb.GET_BLOG_INFO:
            add_progress_m(m)
            self.verb_get_blog_info(m)
        elif m.get_verb() == MessageVerb.GET_WEATHER:
            add_progress_m(m)
            self.verb_get_weather(m)
        return

    def type_process_control(self, m: UnifiedMessage):
        command = m.get_verb()
        if command == MessageVerb.SHUTDOWN:
            m = UnifiedMessage.create(
                priority=0,
                target='COMMS',
                typ='CONTROL',
                verb='SHUTDOWN'
            )
            self.send_to_comms(m)
            add_progress_m(m)
            exit(0)
        elif command == MessageVerb.CHG_BLOG:
            add_progress_m(m)
            self.verb_chg_blog(m)
        elif command == MessageVerb.CHG_RADIO_FREQUENCY:
            add_progress_m(m)
            self.verb_chg_radio_frequency(m)
        elif command == MessageVerb.CHG_USER_FREQUENCY:
            add_progress_m(m)
            self.verb_chg_user_frequency(m)
        return

    def preprocess(self, m: UnifiedMessage):
        if m.get_target() == MessageTarget.BACKEND:
            if m.get_typ() == MessageType.REQUEST:
                self.type_process_request(m)
            elif m.get_typ() == MessageType.CONTROL:
                self.type_process_control(m)
            reload_ui_areas(UiArea.POST_LIST)
            reload_ui_areas(UiArea.POST_CONTENT)
        elif m.get_target() == MessageTarget.COMMS:
            self.send_to_comms(m)

    def check_for_msg(self):
        try:
            m: UnifiedMessage = f2b_q.get(block=False)
            if m:
                logger.debug(f'Received from FRONTEND: {m.get_target()}|{m.get_typ()}|{m.get_verb()}|{m.get_params()}')
                self.preprocess(m)
                f2b_q.task_done()
        except queue.Empty:
            pass
        try:
            m: UnifiedMessage = c2b_q.get(block=True, timeout=0.1)
            if m.get_typ() != MessageType.SIGNAL:
                logger.debug(
                    f'Received from COMMS: ' + f'{m.get_target()}|{m.get_typ()}|{m.get_verb()}|{m.get_params()}'
                )

            if m.get_target() == MessageTarget.BACKEND:
                self.processor.process_rx_message(m)
            c2b_q.task_done()
        except queue.Empty:
            pass


class Backend:
    proc = None

    def __init__(self):
        # Let's trim out old progress entries.
        limit_date = time.time() - (60 * 60 * 24 *2)  # Keep progress for two days.
        post_table = DbTable('progress')
        post_table.delete(where=f"qso_date < {limit_date}")

        self.proc = BeProcessor()
        pass

    def backend_loop(self):
        while True:
            self.proc.check_for_msg()
            time.sleep(SETTINGS.process_wait_ms/1000)
