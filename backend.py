import time
import queue
import re
import logging

from status import Status
from settings import Settings
from message_q import UiArea, UnifiedMessage, MessageTarget, MessageType, MessageVerb, MessageOperator
from db_table import DbTable

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


def add_progress(progress_msg: str, b2f_q: queue.Queue):
    status = Status()
    progress_table = DbTable('progress')

    progress_table.insert(
        row={
            'qso_date': time.time(),
            'blog': status.selected_blog,
            'station': '',
            'frequency': status.radio_frequency,
            'offset': status.offset,
            'message': progress_msg
        }
    )
    status.set_progress_updated()
    reload_ui_areas(UiArea.PROGRESS, b2f_q)


def reload_ui_areas(ui_area: str, b2f_q: queue.Queue):
    status = Status()
    m = UnifiedMessage()

    if ui_area == UiArea.HEADER:
        status.set_hdr_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_HEADER)
    elif ui_area == UiArea.BLOG_LIST:
        status.set_blog_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_BLOG_LIST)
    elif ui_area == UiArea.BLOG_INFO:
        status.set_blog_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_BLOG_INFO)
    elif ui_area == UiArea.POST_LIST:
        status.set_post_list_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_POST_LIST)
    elif ui_area == UiArea.POST_CONTENT:
        status.set_post_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_POST_CONTENT)
    elif ui_area == UiArea.PROGRESS:
        status.set_post_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_PROGRESS)

    logger.info(f"Sending: {m.get_target()}|{m.get_typ()}|{m.get_verb()}")
    b2f_q.put(m)

    return


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
    def __init__(self, b2f_q: queue.Queue):
        self.b2f_q = b2f_q

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
            result = re.findall(reg_ex, m.get_param())

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
                            destination=m.get_destination(),
                            blog=m.get_source(),
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
                        blog=m.get_source(),
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
            result = re.findall(entry, m.get_param())

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
                        blog=m.get_source(),
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

        self.signal_reload(UiArea.POST_LIST)
        self.signal_reload(UiArea.POST_CONTENT)
        self.update_blog_list(blog, line['post_id'], line['post_date'])

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
            status.set_post_updated()

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
            status.set_post_list_updated()

    def process_weather(self, m: UnifiedMessage):
        # ToDo:  Maybe we should add this to the Blog Info window since it relates to the blog server location
        pass

    @staticmethod
    def process_info(blog: str, frequency: int, blog_info: str):
        status = Status()

        # Push the data into the database
        blog_table = DbTable('blog')

        blog_table.update(
            value_dictionary={'info': blog_info},
            where=f"blog='{blog}' AND frequency={frequency}"
        )
        # signal post table update
        status.set_blog_updated()

    def parse_listing(self, m: UnifiedMessage) -> tuple[str, str, str, str, list[dict]]:

        result = re.findall(self.listing_extractor, m.get_param())
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
        return m.get_destination(), cmd, m.get_source(), post_range, entries

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
        status.set_callsign(m.get_param())
        self.signal_reload(UiArea.HEADER)

    def process_note_freq(self, m: UnifiedMessage):
        status = Status()
        status.set_radio_frequency(m.get_param())
        self.signal_reload(UiArea.HEADER)

    def process_note_offset(self, m: UnifiedMessage):
        status = Status()
        status.set_offset(m.get_param())
        self.signal_reload(UiArea.HEADER)

    def signal_reload(self, ui_area):
        reload_ui_areas(ui_area, self.b2f_q)


class BeProcessor:

    post_fields = [
        'qso_date', 'blog', 'station', 'directed_to', 'frequency',
        'offset', 'cmd', 'post_id', 'post_date', 'title', 'body'
    ]

    f2b_q = None
    b2f_q = None
    comms_tx_q = None
    comms_rx_q = None

    def __init__(self, f2b_q: queue.Queue, b2f_q: queue.Queue, comms_tx_q: queue.Queue, comms_rx_q: queue.Queue):
        self.f2b_q = f2b_q
        self.b2f_q = b2f_q
        self.comms_tx_q = comms_tx_q
        self.comms_rx_q = comms_rx_q

    def check_for_msg(self):
        # check for messages from the frontend
        try:
            m: UnifiedMessage = self.f2b_q.get(block=False)
            if m:
                logger.info(f"Received: {m.get_target()}|{m.get_typ()}|{m.get_verb()}")
                self.preprocess(m)
                self.f2b_q.task_done()

        except queue.Empty:
            pass  # nothing on the queue - do nothing

        # check for messages from the comms driver
        try:
            m: UnifiedMessage = self.comms_rx_q.get(block=True, timeout=0.1)  # if no msg waiting, throw an except
            logger.info(f"Received: {m.get_target()}|{m.get_typ()}|{m.get_verb()}")
            logger.debug(m)

            if m.get_target() == MessageTarget.FRONTEND:
                # pass message through to the front end
                logger.info(f"Sending: {m.get_target()}|{m.get_typ()}|{m.get_verb()}")
                self.b2f_q.put(m)

            elif m.get_target() == MessageTarget.BACKEND:
                processor = ServerMsgProcessors(self.b2f_q)
                processor.process_rx_message(m)

            # Even if this message is not for the FRONTEND or BACKEND we must take it off the queue
            self.comms_rx_q.task_done()

        except queue.Empty:
            pass

    def signal_reload(self, ui_area):
        reload_ui_areas(ui_area, self.b2f_q)

    def get_post_from_server(self, m: UnifiedMessage):
        mb_cmd = f"G{m.get_param()}~"
        logger.debug(f"comms: send: {mb_cmd}")
        self.mb_msg_send(destination=m.get_destination(), mb_cmd=mb_cmd)
        return

    def get_list_via_cache(self, m: UnifiedMessage, post_id_list: list) -> None:
        blog = m.get_destination()

        svr_request_list = []  # this is a list of post_ids we will need to request from the server

        range_start = post_id_list[0]
        range_end = post_id_list[len(post_id_list) - 1]

        # form a sql WHERE clause based on command
        where_clause = f"blog='{blog}'"
        where_clause += f" AND post_id>={range_start} and post_id<={range_end}"
        where_clause += " AND title<>'' and post_date>0"

        post_table = DbTable('post')
        db_values = post_table.select(
            where=where_clause,
            group_by='post_id',
            order_by='post_id, body, title', desc=True,
            hdr_list=self.post_fields
        )

        found_post_id = False
        for requested_post_id in post_id_list:
            for row in db_values:
                if requested_post_id == int(row['post_id']):
                    found_post_id = True
                    break

            if not found_post_id:
                svr_request_list.append(requested_post_id)

            found_post_id = False

        if len(svr_request_list) > 0:
            # we need to send a request to the server
            posts_needed = ''
            for post in svr_request_list:
                if len(posts_needed) > 0:
                    posts_needed += ','
                posts_needed += str(post)

            # form a request to get the posts in the svr_request_list
            mb_cmd = f"E{posts_needed}~"
            logger.debug(f"send: {mb_cmd}")

            self.mb_msg_send(destination=m.get_destination(), mb_cmd=mb_cmd)

        return

    def process_list_cmd(self, m: UnifiedMessage):
        status = Status()
        settings = Settings()

        post_ids = []

        if m.get_operator() == MessageOperator.EQ:
            post_ids.append(m.get_param())

        elif m.get_operator() == MessageOperator.RECENT:
            # get the latest post id for this blog
            blog_obj = BlogInstance(m.get_destination(), status.user_frequency)
            latest_post_id, latest_post_date = blog_obj.get_latest_post_details()

            starting_post_id = max(latest_post_id - settings.max_listing + 1, 1)

            for i in range(starting_post_id, latest_post_id + 1):
                post_ids.append(i)

        elif m.get_operator() == MessageOperator.MORE:
            starting_post_id = max(int(m.get_param()) - settings.max_listing, 1)

            for i in range(starting_post_id, int(m.get_param())):
                post_ids.append(i)

        if len(post_ids) > 0:

            if m.get_verb() == MessageVerb.FETCH_LISTING:
                # do we have any of the information in the cache
                self.get_list_via_cache(m, post_ids)

            elif m.get_verb() == MessageVerb.GET_LISTING:
                # get the listing info from the server
                mb_cmd = f"E{','.join(map(str, post_ids))}~"
                logger.debug(f"send: {mb_cmd}")
                self.mb_msg_send(destination=m.get_destination(), mb_cmd=mb_cmd)

        # get the frontend to reload the Post List
        self.signal_reload(UiArea.POST_LIST)
        return

    @staticmethod
    def process_fetch_cmd(req: UnifiedMessage) -> None:
        blog = req.get_destination()
        post_id = int(req.get_param())

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

        # ToDo: we know the current post from the post table entry with is_selected set - we don't need another record
        status = Status()
        status.set_current_post(post_id)

        return

    def process_refresh_cmd(self, m: UnifiedMessage):
        post_id = m.get_param()
        # remove the post from the cache
        post_table = DbTable('post')
        where_clause = f"blog='{m.get_destination()}' AND post_id={post_id} AND body IS NOT NULL"
        post_table.delete(where=where_clause)

        # now we've deleted the cache entry, we can process as though it were a GET
        self.process_fetch_cmd(m)
        return

    def process_query_cmd(self, m: UnifiedMessage):
        logger.debug(f"send: {m.get_destination()} Q")
        self.mb_msg_send(destination=m.get_destination(), mb_cmd="Q")

        return

    def process_info_cmd(self, m: UnifiedMessage):
        logger.debug("comms: send: INFO?")
        self.mb_msg_send(destination=m.get_destination(), mb_cmd="INFO?")

        return

    def process_weather_cmd(self, m: UnifiedMessage):
        logger.debug("comms: send: WX~")
        self.mb_msg_send(destination=m.get_destination(), mb_cmd="WX~")

        return

    def set_hdr_freq(self, frequency: int):
        s = DbTable('status')
        s.update(
            where=None, value_dictionary={
                'radio_frequency': frequency,
                'user_frequency': frequency
            }
        )

        self.signal_reload(UiArea.HEADER)

    def set_hdr_offset(self, offset: int):
        s = DbTable('status')
        s.update(
            where=None, value_dictionary={
                'offset': offset
            }
        )

        self.signal_reload(UiArea.HEADER)

    def set_rig_frequency(self, freq):
        m = UnifiedMessage()
        m.set_many(target=MessageTarget.COMMS, typ=MessageType.CONTROL, verb=MessageVerb.SET_FREQ, param=freq)
        self.send_to_comms(m)

    def set_hdr_callsign(self, callsign: str):
        s = DbTable('status')
        s.update(
            where=None, value_dictionary={
                'callsign': callsign
            }
        )

        self.signal_reload(UiArea.HEADER)

    def mb_msg_send(self, destination: str, mb_cmd: str):

        logger.debug(f"send: {mb_cmd}")

        m = UnifiedMessage(
            target=MessageTarget.COMMS,
            typ=MessageType.MB_MSG,
            verb=MessageVerb.SEND,
            operator=MessageOperator.EQ,
            destination=destination,
            param=mb_cmd
        )

        self.send_to_comms(m)

        return

    def select_blog(self, m: UnifiedMessage):

        # Blog selector is in param field 'blog': blog_name, 'frequency':blog_frequency

        blog = m.get_param()['blog']
        frequency = m.get_param()['frequency']

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

        self.signal_reload(UiArea.BLOG_LIST)
        self.signal_reload(UiArea.BLOG_INFO)

    def process_set_cmd(self, m: UnifiedMessage):

        if m.get_verb() == MessageVerb.CHG_BLOG:
            self.select_blog(m)
            self.signal_reload(UiArea.BLOG_LIST)

        elif m.get_verb() == MessageVerb.CHG_FREQ:
            self.set_rig_frequency(int(m.get_param()))
            self.signal_reload(UiArea.HEADER)

    def preprocess(self, m: UnifiedMessage):
        if m.get_target() == MessageTarget.BACKEND:
            if m.get_typ() == MessageType.REQ:
                self.process_request(m)
            elif m.get_typ() == MessageType.CONTROL:
                self.process_control(m)

        elif m.get_target() == MessageTarget.COMMS:
            # Pass through the message
            self.send_to_comms(m)

        self.signal_reload(UiArea.POST_LIST)
        self.signal_reload(UiArea.POST_LIST)

    def process_request(self, m: UnifiedMessage):
        command = m.get_verb()

        if command == MessageVerb.FETCH_LISTING:
            # Get full list details via the cache
            process_msg = f"{m.get_verb()} {m.get_operator()} {m.get_param()}~"
            add_progress(process_msg, self.b2f_q)
            self.process_list_cmd(m)

        elif command == MessageVerb.GET_LISTING:
            # Get full list details not using the cache
            process_msg = f"{m.get_verb()} {m.get_operator()} {m.get_param()}~"
            add_progress(process_msg, self.b2f_q)
            self.process_list_cmd(m)

        elif command == MessageVerb.FETCH_POST:
            # Fetch post(s)
            process_msg = f"{m.get_verb()} {m.get_operator()} {m.get_param()}~"
            add_progress(process_msg, self.b2f_q)
            self.process_fetch_cmd(m)
            self.signal_reload(UiArea.POST_CONTENT)

        elif command == MessageVerb.GET_POST:
            # Get post(s)
            process_msg = f"{m.get_verb()} {m.get_operator()} {m.get_param()}~"
            add_progress(process_msg, self.b2f_q)
            self.get_post_from_server(m)

        elif command == MessageVerb.GET_BLOG_INFO:
            # Get information from the server
            process_msg = f"{m.get_verb()}"
            add_progress(process_msg, self.b2f_q)
            self.process_info_cmd(m)

        elif command == MessageVerb.GET_WEATHER:
            # Request a weather report - results in G0~ to the server
            process_msg = f"{m.get_verb()}"
            add_progress(process_msg, self.b2f_q)
            self.process_weather_cmd(m)

        return

    def process_control(self, m: UnifiedMessage):
        command = m.get_verb()

        if command == MessageVerb.SHUTDOWN:
            m = UnifiedMessage()
            m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.CONTROL, verb=MessageVerb.SHUTDOWN)
            self.send_to_comms(m)
            add_progress(command, self.b2f_q)
            exit(0)

        elif command == MessageVerb.CHG_BLOG:
            # Switch to a blog (internal - no server command is sent)
            process_msg = f"{command}"
            add_progress(process_msg, self.b2f_q)
            self.process_set_cmd(m)

        elif command == MessageVerb.CHG_FREQ:
            # Switch to a blog (internal - no server command is sent)
            process_msg = f"{command}"
            add_progress(process_msg, self.b2f_q)
            self.process_set_cmd(m)

        elif command == MessageVerb.GET_BLOG_INFO:
            # Query command to elicit an announcement from all MB servers
            process_msg = f"{command}"
            add_progress(process_msg, self.b2f_q)
            self.process_query_cmd(m)

        return

    def send_to_comms(self, m: UnifiedMessage):
        logger.info(f"Sending: {m.get_target()}|{m.get_typ()}|{m.get_verb()}")
        self.comms_tx_q.put(m)


class Backend:

    proc = None  # for backend processor

    def __init__(self, f2b_q: queue.Queue, b2f_q: queue.Queue, comms_tx_q: queue.Queue, m_q: queue.Queue):
        self.proc = BeProcessor(f2b_q, b2f_q, comms_tx_q, m_q)
        pass

    def backend_loop(self):
        while True:
            # check for f2b message and process
            self.proc.check_for_msg()
            time.sleep(0.2)  # we need this else the backend thread hogs the cpu
