import time
import queue
import re
import logging

from status import Status
from settings import Settings
from message_q import f2b_q, b2f_q, b2c_q, c2b_q, UiArea, UnifiedMessage,\
    MessageTarget, MessageType, MessageVerb, MessageOperator, MessageParameter
from db_table import DbTable
from general_functions import add_progress_m, reload_ui_areas

logger = logging.getLogger(__name__)


# compress_date takes epoch as sole argument
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


class BlogInstance:

    latest_post_id: int = None
    latest_post_date: int = None
    last_seen: int = None
    selected: int = None

    blog_field = [
        'blog',
        'station',
        'frequency',
        'snr',
        'latest_post_id',
        'latest_post_date',
        'last_seen_date',
        'is_selected'
    ]

    def __init__(self, name: str, freq: int):

        blog_table = DbTable('blog')
        results = blog_table.select(
            where=f"blog='{name}' AND frequency={freq}",
            limit=1, hdr_list=self.blog_field
        )
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

    listing_extractor = r"^([+-])([EL])([\d,]*)~\n*([\S\s]+)"
    post_extractor = r"^([+-])(G)(\d+)~\n*([\S\s]+)"
    weather_extractor = r"^([+-])(WX)~\n*([\S\s]+)"
    info_extractor = r"^(INFO) +([\S\s]+)"

    announce_extractor = r"^(\d+) +(\d{6})"
    announce_extractor_old = r"^([A-Z,0-9/]+) +(\d+) +(\d{4}-\d{2}-\d{2})"

    qso_fields = ['qso_date', 'blog', 'station', 'directed_to', 'frequency',
                  'offset', 'cmd', 'post_id', 'post_date', 'title', 'body']

    # we use __init__ to preload some metadata we will need to create a qso entry
    def __init__(self):
        pass

    def process_rx_message(self, m: UnifiedMessage):

        if m.get_typ() == MessageType.MB_MSG:
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

    def process_inform(self, m: UnifiedMessage):

        status = Status()

        inform_patterns = [self.listing_extractor, self.post_extractor, self.weather_extractor, self.info_extractor]

        for reg_ex in inform_patterns:
            # try to match the request
            result = re.findall(reg_ex, m.get_param(MessageParameter.MB_MSG))

            if len(result) == 0:
                continue  # We haven't matched the message from the mb server.

            else:
                # the result is a list of tuples
                result = list(result[0])  # pull the 1st result out of the list and convert to a list

                # process if the result was positive
                if result[0] == '+':
                    mb_cmd = result[1]  # The cmd we sent to the microblog server to get this information

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
                            cmd=cmd,
                            blog=blog,
                            post_range=post_range,
                            lines=lines
                        )
                        self.signal_reload(UiArea.POST_LIST)

                elif result[0] == 'INFO':
                    self.process_info(
                        blog=m.get_param(MessageParameter.SOURCE),
                        frequency=status.radio_frequency,
                        blog_info=result[1]
                    )
                self.signal_reload(UiArea.BLOG_INFO)

                break

        return

    def process_announcement(self, m: UnifiedMessage) -> None:
        # we need to support two formats of announcement
        # old:  blog_name post_id date_time
        # new:  post_id date_time

        announcement_patterns = [self.announce_extractor, self.announce_extractor_old]

        for entry in announcement_patterns:
            # try to match the request
            result = re.findall(entry, m.get_param(MessageParameter.MB_MSG))

            if len(result) > 0:
                is_valid = False
                post_id = 0
                post_date = 0

                result = list(result[0])  # Dereference to match from the first group

                if len(result) == 2:
                    # We have a new style announcement
                    post_id = int(result[0])
                    post_date = time.mktime(time.strptime(result[1] + " GMT", "%y%m%d %Z"))
                    is_valid = True

                elif len(result) == 3:
                    # We have an old style announcement
                    post_id = int(result[1])
                    post_date = time.mktime(time.strptime(result[2] + " GMT", "%Y-%m-%d %Z"))
                    is_valid = True

                if is_valid:
                    # We have a valid announcement
                    self.update_blog_list(
                        blog=m.get_param(MessageParameter.SOURCE),
                        post_id=post_id,
                        post_date=post_date
                    )
                    self.signal_reload(UiArea.BLOG_LIST)

        return

    def process_listing(self, destination: str, cmd: str, blog: str, post_range: str, lines: []):
        status = Status()
        post_table = DbTable('post')
        qso_date = time.time()

        for line in lines:

            # if we already have an entry for this post we only want to replace it
            # if this listing was directed_to this station
            db_values = post_table.select(
                where=f"blog='{blog}' AND post_id={line['post_id']}",
                hdr_list=['body', 'is_selected']
            )

            if len(db_values) == 0:
                # Delete any existing entry and create a new one
                post_table.delete(
                    where=f"blog='{blog}' AND post_id={line['post_id']}"
                )

                row = {
                    'qso_date': qso_date,
                    'blog': blog, 'station': blog,
                    'directed_to': destination,
                    'frequency': status.radio_frequency, 'offset': status.offset,
                    'cmd': cmd + post_range,
                    'post_id': line['post_id'], 'post_date': line['post_date'], 'title': line['title'], 'body': '',
                    'is_selected': 0
                }
                post_table.insert(row)

            elif destination == status.callsign:
                # Delete any existing entry and create a new one
                post_table.delete(
                    where=f"blog='{blog}' AND post_id={line['post_id']}"
                )

                row = {
                    'qso_date': qso_date, 'blog': blog, 'station': blog,
                    'directed_to': destination,
                    'frequency': status.radio_frequency, 'offset': status.offset,
                    'cmd': cmd,
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

        # do we have the title for this blog

        db_values = post_table.select(
            where=f"blog='{blog}' AND post_id={post_id}",
            limit=1,
            hdr_list=['post_id']
        )

        if len(db_values) > 0:
            post_table.update(
                value_dictionary={'body': body},
                where=f"blog='{blog}' AND post_id={post_id}"
            )
            # signal post table update
            reload_ui_areas(UiArea.POST_CONTENT)

        else:
            post_table.insert(
                row={
                    'qso_date': 0,
                    'blog': blog,
                    'station': blog,
                    'directed_to': destination,
                    'frequency': status.radio_frequency,
                    'offset': status.offset,
                    'cmd': 'G',
                    'post_id': post_id,
                    'post_date': 0.0,
                    'title': f"** {body[:20]}",
                    'body': body,
                    'is_selected': 0
                   },
            )
            # signal post table update
            reload_ui_areas(UiArea.POST_LIST)

    def process_weather(self, m: UnifiedMessage):
        # ToDo:  Maybe we should add this to the Blog Info window since it relates to the blog server location
        pass

    @staticmethod
    def process_info(blog: str, frequency: int, blog_info: str):
        # Push the data into the database
        blog_table = DbTable('blog')

        blog_table.update(
            value_dictionary={'info': blog_info},
            where=f"blog='{blog}' AND frequency={frequency}"
        )
        # signal post table update
        reload_ui_areas(UiArea.BLOG_INFO)

    def parse_listing(self, m: UnifiedMessage) -> tuple[str, str, str, str, list[dict]]:

        result = re.findall(self.listing_extractor, m.get_param(MessageParameter.MB_MSG))
        result = list(result[0])  # pull the 1st result out of the list and convert to a list

        cmd: str = result[1]
        post_range: str = result[2]
        body: str = result[3]

        entries: list[dict] = []  # Will be used to hold a list of dictionaries
        # [{'post_id': 123, 'post_date': 1768637136, 'title': 'Fred goes to town' }, ...]

        lines = body.split('\n')  # this is the list output
        for line in lines:

            if line == 'NO POSTS FOUND':
                entries.append({'post_id': -1, 'post_date': 0, 'title': 'NO POSTS FOUND'})
                break

            if cmd == 'E':
                details = re.findall(r"(\d+) - (\d{4}-\d{2}-\d{2}) - ([\S\s]+)", line)

                if len(details) > 0:
                    post_id = int(details[0][0])
                    post_date = time.mktime(time.strptime(details[0][1], "%Y-%m-%d"))
                    title = details[0][2]
                    entries.append({'post_id': post_id, 'post_date': post_date, 'title': title})
                else:
                    logger.info(f"Received extended listing is too corrupt to interpret: {line}")
                    continue

            else:
                details = re.findall(r"(\d+) - ([\S\s]+)", line)

                if len(details[0]) > 0:
                    post_id = int(details[0][0])
                    post_date = 0
                    title = details[0][1]
                    entries.append({'post_id': post_id, 'post_date': post_date, 'title': title})
                else:
                    logger.info(f"Received listing is too corrupt to interpret: {line}")
                    continue

        # process_listing needs destination: str, cmd: str, blog: str, post_range: str, lines: []
        return m.get_param(MessageParameter.DESTINATION), cmd, m.get_param(MessageParameter.SOURCE), post_range, entries

    def update_blog_list(self, blog: str, post_id: int, post_date: int) -> None:
        status = Status()

        # do we have a blog entry for this blog at this station
        blog_table = DbTable('blog')
        results = blog_table.select(
            where=f"blog='{blog}' AND frequency={status.radio_frequency}",
            limit=1, hdr_list=['latest_post_id', 'latest_post_date']
        )
        if len(results) > 0:
            latest_post_id = results[0]['latest_post_id']

            # Although the post_id in an @MB Announcement should always be the latest, if we are updating
            # the blog details based on other details, we only want to do that if the post ID in that message
            # is later than or equal to that of the existing blog list entry.
            # We need to cover the equal to variant in case we don't have the latest_post_date in the current
            # blog list entry, but we do have that detail in the message we are handling.
            if post_id >= latest_post_id:
                # update the existing entry
                blog_table.update(
                    value_dictionary={
                        'latest_post_id': post_id,
                        'latest_post_date': post_date,
                        'last_seen_date': time.time()
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
            # no existing blog entry so create one
            blog_table.insert(
                row={'blog': blog, 'station': blog, 'frequency': status.radio_frequency,
                     'snr': 0, 'latest_post_id': post_id,
                     'latest_post_date': post_date, 'last_seen_date': time.time(),
                     'is_selected': 0, 'info': ''}
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
    def signal_reload(ui_area):
        reload_ui_areas(ui_area)


class BeProcessor:

    post_fields = [
        'qso_date', 'blog', 'station', 'directed_to', 'frequency',
        'offset', 'cmd', 'post_id', 'post_date', 'title', 'body'
    ]

    def __init__(self, ):
        pass

    # ---- functions related to fetch and get listing ----

    def listing_is_in_cache(self, blog, post_id) -> bool:
        # form a sql WHERE clause based on command
        where_clause = f"blog='{blog}'"
        where_clause += f" AND post_id={post_id}"
        where_clause += " AND title<>'' and post_date>0"

        post_table = DbTable('post')
        db_values = post_table.select(
            where=where_clause,
            group_by='post_id',
            order_by='post_id, body, title', desc=True,
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
            pass  # do nothing as we want to just send E~

        elif m.get_param(MessageParameter.OPERATOR) == MessageOperator.MORE:
            post_id = m.get_param(MessageParameter.POST_ID)
            starting_post_id = max(int(post_id) - settings.max_listing, 1)
            for i in range(starting_post_id, int(post_id)):
                post_list.append(i)

        return post_list

    @staticmethod
    def get_listing_command(post_id_list: []) -> str:

        if len(post_id_list) > 0:
            post_list_string = ','.join(map(str, post_id_list))
        else:
            post_list_string = ''

        # get the listing info from the server
        mb_cmd = f"E{post_list_string}~"

        return mb_cmd

    def verb_fetch_listing(self, m: UnifiedMessage):
        blog = m.get_param(MessageParameter.DESTINATION)
        post_id_list = self.get_post_id_list(m)

        # if we don't get a list we should bail here
        if len(post_id_list) == 0:
            return

        svr_request_list = []  # this is a list of post_ids we will need to request from the server

        for post_id in post_id_list:
            if self.listing_is_in_cache(blog, post_id):
                continue
            else:
                svr_request_list.append(post_id)

        if len(svr_request_list) == 0:
            return

        # we need to send a request to the server
        # form a request to get the posts in the svr_request_list
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

    # ---- functions related to the remaining mb messages ----

    @staticmethod
    def verb_fetch_post(m: UnifiedMessage) -> None:
        blog = m.get_param(MessageParameter.DESTINATION)
        post_id = int(m.get_param(MessageParameter.POST_ID))

        # set this as the selected post
        post_table = DbTable('post')
        post_table.update(
            where=f"blog='{blog}'",
            value_dictionary={'is_selected': 0}
        )
        post_table.update(
            where=f"blog='{blog}' AND post_id={post_id}",
            value_dictionary={'is_selected': 1}
        )

        return

    def verb_get_post(self, m: UnifiedMessage) -> None:
        mb_cmd = f"G{m.get_param(MessageParameter.POST_ID)}~"
        self.mb_msg_send(destination=m.get_param(MessageParameter.DESTINATION), mb_cmd=mb_cmd)
        return

    def verb_get_weather(self, m: UnifiedMessage) -> None:
        self.mb_msg_send(destination=m.get_param(MessageParameter.DESTINATION), mb_cmd="WX~")

        return

    def verb_get_blog_info(self, m: UnifiedMessage) -> None:
        logger.debug("comms: send: INFO?")
        self.mb_msg_send(destination=m.get_param(MessageParameter.DESTINATION), mb_cmd="INFO?")

        return

    def verb_scan(self, m: UnifiedMessage) -> None:
        self.mb_msg_send(destination=m.get_param(MessageParameter.DESTINATION), mb_cmd="Q")

        return

    # ---- functions related to control ----

    @staticmethod
    def set_hdr_freq(frequency: int):
        s = DbTable('status')
        s.update(
            where=None, value_dictionary={
                'radio_frequency': frequency,
                'user_frequency': frequency
            }
        )
        reload_ui_areas(UiArea.HEADER)

    @staticmethod
    def set_hdr_offset(offset: int):
        s = DbTable('status')
        s.update(
            where=None, value_dictionary={
                'offset': offset
            }
        )
        reload_ui_areas(UiArea.HEADER)

    def set_rig_frequency(self, frequency: int):
        m = UnifiedMessage.create(
            target="COMMS",
            typ="CONTROL",
            verb="SET_FREQ",
            params={"frequency": frequency}
        )
        self.send_to_comms(m)

    @staticmethod
    def set_hdr_callsign(callsign: str):
        s = DbTable('status')
        s.update(
            where=None, value_dictionary={
                'callsign': callsign
            }
        )
        reload_ui_areas(UiArea.HEADER)

    def mb_msg_send(self, destination: str, mb_cmd: str):

        m = UnifiedMessage(
            target=MessageTarget.COMMS,
            typ=MessageType.MB_MSG,
            verb=MessageVerb.SEND,
            params={
                MessageParameter.DESTINATION: destination,
                MessageParameter.MB_MSG: mb_cmd
            }
        )

        logger.info(f"Sending to COMMS: {m.get_target()}|{m.get_typ()}|{m.get_verb()}|{m.get_params()}")

        self.send_to_comms(m)

        return

    @staticmethod
    def select_blog(m: UnifiedMessage):

        # Blog selector is in param field 'blog': blog_name, 'frequency':blog_frequency

        blog = m.get_param(MessageParameter.BLOG)
        frequency = m.get_param(MessageParameter.FREQUENCY)

        if len(blog) > 0:
            s = DbTable('status')
            s.update(
                where=None, value_dictionary={
                    'selected_blog': blog,
                    'user_frequency': frequency
                }
            )

            # update the selected row
            b = DbTable('blog')
            b.update(where=None, value_dictionary={'is_selected': 0})
            b.update(where=f"blog='{blog}' AND frequency={frequency}",
                     value_dictionary={'is_selected': 1})

            s.update(
                where=None,
                value_dictionary={
                    'hdr_updated': time.time(),
                    'progress_updated': time.time(),
                    'blog_updated': time.time()
                }
            )

        reload_ui_areas(UiArea.BLOG_LIST)
        reload_ui_areas(UiArea.BLOG_INFO,)

    def verb_chg_blog(self, m: UnifiedMessage) -> None:
        if m.get_verb() == MessageVerb.CHG_BLOG:
            self.select_blog(m)
            reload_ui_areas(UiArea.BLOG_LIST,)

            return

    def verb_chg_radio_frequency(self, m: UnifiedMessage) -> None:
        status = Status()

        self.set_rig_frequency(m.get_param(MessageParameter.FREQUENCY))
        reload_ui_areas(UiArea.HEADER,)
        status.set_radio_frequency(m.get_param(MessageParameter.FREQUENCY))

        return

    @staticmethod
    def verb_chg_user_frequency(m: UnifiedMessage) -> None:
        status = Status()
        status.set_user_frequency(m.get_param(MessageParameter.FREQUENCY))

        return

    @staticmethod
    def send_to_comms(m: UnifiedMessage):
        logger.info(f"Sending to COMMS: {m.get_target()}|{m.get_typ()}|{m.get_verb()}|{m.get_params()}")
        b2c_q.put(m)

    def type_process_request(self, m: UnifiedMessage):

        if m.get_verb() == MessageVerb.FETCH_LISTING:
            # Get full list details via the cache
            add_progress_m(m)
            self.verb_fetch_listing(m)

        elif m.get_verb() == MessageVerb.GET_LISTING:
            # Get full list details not using the cache
            add_progress_m(m)
            self.verb_get_listing(m)

        elif m.get_verb() == MessageVerb.FETCH_POST:
            # Fetch post(s)
            add_progress_m(m)
            self.verb_fetch_post(m)

        elif m.get_verb() == MessageVerb.GET_POST:
            # Get post(s)
            add_progress_m(m)
            self.verb_get_post(m)

        elif m.get_verb() == MessageVerb.SCAN:
            # Get information from the server
            add_progress_m(m)
            self.verb_scan(m)

        elif m.get_verb() == MessageVerb.GET_BLOG_INFO:
            # Get information from the server
            add_progress_m(m)
            self.verb_get_blog_info(m)

        elif m.get_verb() == MessageVerb.GET_WEATHER:
            # Request a weather report - results in G0~ to the server
            add_progress_m(m)
            self.verb_get_weather(m)

        return

    def type_process_control(self, m: UnifiedMessage):
        command = m.get_verb()

        if command == MessageVerb.SHUTDOWN:
            m = UnifiedMessage.create(target="COMMS", typ="CONTROL", verb="SHUTDOWN")
            self.send_to_comms(m)
            add_progress_m(m)
            exit(0)

        elif command == MessageVerb.CHG_BLOG:
            # Switch to a blog (internal - no server command is sent)
            add_progress_m(m)
            self.verb_chg_blog(m)

        elif command == MessageVerb.CHG_RADIO_FREQUENCY:
            # Switch to a blog (internal - no server command is sent)
            add_progress_m(m)
            self.verb_chg_radio_frequency(m)

        elif command == MessageVerb.CHG_USER_FREQUENCY:
            # Switch to a blog (internal - no server command is sent)
            add_progress_m(m)
            self.verb_chg_user_frequency(m)

        return

    def preprocess(self, m: UnifiedMessage):
        if m.get_target() == MessageTarget.BACKEND:
            if m.get_typ() == MessageType.REQUEST:
                self.type_process_request(m)
            elif m.get_typ() == MessageType.CONTROL:
                self.type_process_control(m)
            reload_ui_areas(UiArea.POST_LIST,)
            reload_ui_areas(UiArea.POST_CONTENT,)

        elif m.get_target() == MessageTarget.COMMS:
            # Pass through the message
            self.send_to_comms(m)

    def check_for_msg(self):
        # check for messages from the frontend
        try:
            m: UnifiedMessage = f2b_q.get(block=False)
            if m:
                logger.info(f"Received from FRONTEND: {m.get_target()}|{m.get_typ()}|{m.get_verb()}|{m.get_params()}")
                self.preprocess(m)
                f2b_q.task_done()

        except queue.Empty:
            pass  # nothing on the queue - do nothing

        # check for messages from the comms driver
        try:
            m: UnifiedMessage = c2b_q.get(block=True, timeout=0.1)  # if no msg waiting, throw an except

            if m.get_typ() != MessageType.SIGNAL:
                logger.info(
                    f"Received from COMMS: " +
                    f"{m.get_target()}|{m.get_typ()}|{m.get_verb()}|{m.get_params()}"
                )

            if m.get_target() == MessageTarget.FRONTEND:
                # pass message through to the front end
                log_message = f"Sending to FRONTEND: " \
                        f"{m.get_target()}|{m.get_typ()}|{m.get_verb()}|{m.get_params()}"

                # When at INFO level of logging, we don't want to log all the SIGNALS from COMMS
                if m.get_typ() != MessageType.SIGNAL:
                    logger.info(log_message)
                else:
                    logger.debug(log_message)

                b2f_q.put(m)

            elif m.get_target() == MessageTarget.BACKEND:
                processor = ServerMsgProcessors()
                processor.process_rx_message(m)

            # Even if this message is not for the FRONTEND or BACKEND we must take it off the queue
            c2b_q.task_done()

        except queue.Empty:
            pass


class Backend:

    proc = None  # for backend processor

    def __init__(self):
        self.proc = BeProcessor()
        pass

    def backend_loop(self):
        while True:
            # check for f2b message and process
            self.proc.check_for_msg()
            time.sleep(0.2)  # we need this else the backend thread hogs the cpu