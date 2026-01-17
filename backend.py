import time
import queue
import re
import logging

from status import Status
from settings import Settings
from message_q import UnifiedMessage, GuiMessage, MessageTarget, MessageType, MessageVerb, MessageOperator
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
    reload_ui_areas('progress', b2f_q)


def reload_ui_areas(ui_area: str, b2f_q: queue.Queue):
    status = Status()
    m = UnifiedMessage()

    if ui_area == 'header':
        status.set_hdr_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_HEADER)
    elif ui_area == 'blog_list':
        status.set_blog_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_BLOG_LIST)
    elif ui_area == 'blog_info':
        status.set_blog_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_BLOG_INFO)
    elif ui_area == 'post_list':
        status.set_post_list_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_POST_LIST)
    elif ui_area == 'post_content':
        status.set_post_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_POST_CONTENT)
    elif ui_area == 'progress':
        status.set_post_updated()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=MessageVerb.RELOAD_PROGRESS)

    b2f_q.put(m)

    return


class Blog:

    name = ''

    def __init__(self, blog_name):
        self.name = blog_name


class BlogInstance(Blog):

    def __init__(self, blog_name):
        super().__init__(
            blog_name
        )


class BlogInstanceFQ(BlogInstance):

    freq = None
    snr = None
    latest_post_id = None
    latest_post_date = None
    last_seen = None
    is_selected = None

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

    def __init__(self, blog_name: str, blog_freq: int):
        super().__init__(blog_name)
        self.freq = blog_freq

        blog_table = DbTable('blog')
        results = blog_table.select(
            where=f"blog='{self.name}' AND frequency={self.freq}",
            limit=1, hdr_list=self.blog_field
        )
        if len(results) > 0:
            self.snr = results[0]['snr']
            self.latest_post_id = results[0]['latest_post_id']
            self.latest_post_date = results[0]['latest_post_date']
            self.last_seen = results[0]['last_seen_date']
            self.is_selected = results[0]['is_selected']

    def get_latest_post_details(self):
        return self.latest_post_id, self.latest_post_date

    def get_last_seen(self):
        return self.last_seen


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
            pass

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

                    elif mb_cmd == 'E' or mb_cmd == 'L':
                        destination, cmd, blog, post_range, lines = self.parse_listing(m)
                        self.process_listing(
                            destination=destination,
                            cmd=cmd,
                            blog=blog,
                            post_range=post_range,
                            lines=lines
                        )

                elif result[0] == 'INFO':
                    self.process_info(
                        blog=m.get_source(),
                        frequency=status.radio_frequency,
                        blog_info=result[1]
                    )

                break

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

            self.signal_reload('post_list')
            self.signal_reload('post_content')
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
        return

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
        self.signal_reload('blog_list')

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

    def signal_reload(self, ui_area):
        reload_ui_areas(ui_area, self.b2f_q)

    def get_post_from_server(self, req: GuiMessage):
        mb_cmd = f"G{req.get_post_id()}~"
        logger.debug(f"comms: send: {mb_cmd}")
        self.mb_msg_send(destination=req.blog, mb_cmd=mb_cmd)
        return

    def get_list_via_cache(self, req: GuiMessage, post_id_list: list) -> None:
        blog = req.get_blog()

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

            self.mb_msg_send(destination=req.blog, mb_cmd=mb_cmd)

        return

    def process_list_cmd(self, req: GuiMessage):
        settings = Settings()

        post_ids = []

        if req.get_op() == MessageOperator.EQ:
            post_ids.append(req.get_post_id())

        elif req.get_op() == MessageOperator.GT:
            for i in range(settings.max_listing):
                post_ids.append(req.get_post_id() + 1 + i)

        elif req.get_op() == MessageOperator.RECENT:
            # get the latest post id for this blog
            blog_obj = BlogInstanceFQ(req.get_blog(), req.get_frequency())
            latest_post_id, latest_post_date = blog_obj.get_latest_post_details()

            starting_post_id = max(latest_post_id - settings.max_listing + 1, 1)

            for i in range(starting_post_id, latest_post_id + 1):
                post_ids.append(i)

        elif req.get_op() == MessageOperator.MORE:
            starting_post_id = max(req.get_post_id() - settings.max_listing, 1)

            for i in range(starting_post_id, req.get_post_id()):
                post_ids.append(i)

        if len(post_ids) > 0:

            if req.get_cmd() == 'E':
                # do we have any of the information in the cache
                self.get_list_via_cache(req, post_ids)

            elif req.get_cmd() == 'D':
                # get the listing info from the server
                mb_cmd = f"E{req.get_post_id()}~"
                logger.debug(f"send: {mb_cmd}")
                self.mb_msg_send(destination=req.blog, mb_cmd=mb_cmd)

        # get the frontend to reload the Post List
        self.signal_reload('post_list')
        return

    def process_extended_cmd(self, req: GuiMessage):
        self.process_list_cmd(req)

    @staticmethod
    def process_fetch_cmd(req: GuiMessage) -> None:
        blog = req.get_blog()
        post_id = req.get_post_id()

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

    def process_refresh_cmd(self, req: GuiMessage):
        post_id = req.get_post_id()
        # remove the post from the cache
        post_table = DbTable('post')
        where_clause = f"blog='{req.get_blog()}' AND post_id={post_id} AND body IS NOT NULL"
        post_table.delete(where=where_clause)

        # now we've deleted the cache entry, we can process as though it were a GET
        req.cmd = 'G'
        self.process_fetch_cmd(req)
        return

    def process_query_cmd(self, req: GuiMessage):
        blog = req.blog

        logger.debug(f"send: {blog} Q")

        self.mb_msg_send(destination=blog, mb_cmd="Q")

        return

    def process_info_cmd(self, req: GuiMessage):
        blog = req.blog

        logger.debug("comms: send: INFO?")

        self.mb_msg_send(destination=blog, mb_cmd="INFO?")

        return

    def process_weather_cmd(self, req: GuiMessage):
        blog = req.blog

        logger.debug("comms: send: WX~")

        self.mb_msg_send(destination=blog, mb_cmd="WX~")

        return

    def set_hdr_freq(self, frequency: int):
        s = DbTable('status')
        s.update(
            where=None, value_dictionary={
                'radio_frequency': frequency,
                'user_frequency': frequency
            }
        )

        self.signal_reload('header')

    def set_hdr_offset(self, offset: int):
        s = DbTable('status')
        s.update(
            where=None, value_dictionary={
                'offset': offset
            }
        )

        self.signal_reload('header')

    def set_rig_frequency(self, freq):
        m = UnifiedMessage()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.CONTROL, verb=MessageVerb.SET_FREQ, param=freq)
        self.comms_tx_q.put(m)

    def set_hdr_callsign(self, callsign: str):
        s = DbTable('status')
        s.update(
            where=None, value_dictionary={
                'callsign': callsign
            }
        )

        self.signal_reload('header')

    def mb_msg_send(self, destination: str, mb_cmd: str):

        status = Status()
        frequency = status.radio_frequency

        logger.debug(f"send: {mb_cmd}")

        m = UnifiedMessage(
            target=MessageTarget.COMMS,
            typ=MessageType.MB_MSG,
            verb=MessageVerb.SEND,
            operator=MessageOperator.EQ,
            destination=destination,
            frequency=frequency,
            param=mb_cmd
        )

        self.comms_tx_q.put(m)

        return

    def select_blog(self, req: GuiMessage):

        blog = req.get_blog()
        frequency = req.get_frequency()

        if len(blog) > 0:
            s = DbTable('status')
            s.update(
                where=None, value_dictionary={
                    'selected_blog': blog,
                    'selected_station': blog,
                    'radio_frequency': frequency,
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

            # signal to the comms driver that the frequency must be changed
            self.set_rig_frequency(frequency)

    def process_set_cmd(self, req: GuiMessage):

        if len(req.get_blog()) > 0:
            self.select_blog(req)
        elif req.get_frequency() > 0:
            self.set_rig_frequency(req.get_frequency())

        self.signal_reload('blog_list')

    def process_config_cmd(self, msg: GuiMessage):
        pass

    def process_scan_cmd(self, msg: GuiMessage):
        pass

    def preprocess(self, msg_object: GuiMessage):
        command = msg_object.get_cmd()
        msg_prefix = "Received command from the frontend: "

        if command == 'X':
            m = UnifiedMessage()
            m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.CONTROL, verb=MessageVerb.SHUTDOWN)
            self.comms_tx_q.put(m)

            logger.info(f"{msg_prefix}{command}")
            add_progress(command, self.b2f_q)
            exit(0)

        elif command == 'L':
            # Get abbreviated list
            process_msg = f"{command}{msg_object.get_op().value}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_list_cmd(msg_object)

        elif command == 'D':
            # Get full list details not using the cache
            process_msg = f"{command}{msg_object.get_op().value}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_extended_cmd(msg_object)

        elif command == 'E':
            # Get full list details using the cache
            process_msg = f"{command}{msg_object.get_op().value}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_extended_cmd(msg_object)

        elif command == 'F':
            # Fetch post(s)
            process_msg = f"{command}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_fetch_cmd(msg_object)
            self.signal_reload('post_content')

        elif command == 'G':
            # Get post(s)
            process_msg = f"{command}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.get_post_from_server(msg_object)

        elif command == 'R':
            # Refresh a post (results in sending a Get to the server)
            process_msg = f"{command}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_refresh_cmd(msg_object)

        elif command == 'I':
            # Get information from the server
            process_msg = f"INFO?"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_info_cmd(msg_object)

        elif command == 'S':
            # Switch to a blog (internal - no server command is sent)
            process_msg = f"{command}"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_set_cmd(msg_object)

        elif command == 'C':
            # Change the config - not implemented
            process_msg = f"{command}"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_config_cmd(msg_object)

        elif command == 'P':
            # Initiate a Scan - not implemented
            process_msg = f"{command}"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_scan_cmd(msg_object)

        elif command == 'Q':
            # Query command to elicit an announcement from all MB servers
            process_msg = f"{command}"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_query_cmd(msg_object)

        elif command == 'WX':
            # Request a weather report - results in G0~ to the server
            process_msg = f"{command}"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg, self.b2f_q)
            self.process_weather_cmd(msg_object)

        self.signal_reload('post_list')
        self.signal_reload('post_content')

    def check_for_msg(self):
        # check for messages from the frontend
        try:
            fe_msg: GuiMessage = self.f2b_q.get(block=False)
            if fe_msg:
                logger.debug(fe_msg.get_cmd())
                self.preprocess(fe_msg)
                self.f2b_q.task_done()

        except queue.Empty:
            pass  # nothing on the queue - do nothing

        # check for messages from the comms driver
        try:
            m: UnifiedMessage = self.comms_rx_q.get(block=True, timeout=0.1)  # if no msg waiting, throw an except
            logger.debug(m)

            if m.get_target() == MessageTarget.FRONTEND:
                # pass message through to the front end
                self.b2f_q.put(m)

            elif m.get_target() == MessageTarget.BACKEND:
                processor = ServerMsgProcessors(self.b2f_q)
                processor.process_rx_message(m)

            # Even if this message is not for the FRONTEND or BACKEND we must take it off the queue
            self.comms_rx_q.task_done()

        except queue.Empty:
            pass


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
