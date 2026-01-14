import time
import queue
import re

import logging
logger = logging.getLogger(__name__)

from status import Status
from settings import Settings
from message_q import CommsMessage, GuiMessage
from db_table import DbTable


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


def add_progress(progress_msg: str):
    status = Status()
    progress_table = DbTable('progress')

    progress_table.insert(
        row={
            'qso_date': time.time(),
            'blog': status.selected_blog,
            'station': status.selected_station,
            'frequency': status.radio_frequency,
            'offset': status.offset,
            'message': progress_msg
        }
    )
    status.set_progress_updated()


class Blog:

    name = ''

    def __init__(self, blog_name):
        self.name = blog_name


class BlogInstance(Blog):

    station = None

    def __init__(self, blog_name, blog_station):
        super().__init__(
            blog_name
        )
        self.station = blog_station


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

    def __init__(self, blog_name: str, blog_station: str, blog_freq: int):
        super().__init__(blog_name, blog_station)
        self.freq = blog_freq

        blog_table = DbTable('blog')
        results = blog_table.select(
            where=f"blog='{self.name}' AND station='{self.station}' AND frequency={self.freq}",
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

    qso_fields = ['qso_date', 'blog', 'station', 'directed_to', 'frequency',
                  'offset', 'cmd', 'post_id', 'post_date', 'title', 'body']

    mb_status = None
    qso_date = 0
    blog = ''
    station = ''
    directed_to = ''
    frequency = 0
    offset = 0
    snr = 0
    cmd = ''
    post_id = 0
    post_date = 0
    title = ''
    body = ''

    rsp = ''

    # we use __init__ to preload some metadata we will need to create a qso entry
    def __init__(self, js8_msg: CommsMessage, b2f_q: queue.Queue):
        self.b2f_q = b2f_q
        self.mb_status = Status()
        self.qso_date = js8_msg.get_ts()
        self.station = js8_msg.get_source()
        self.directed_to = js8_msg.get_destination()
        self.frequency = js8_msg.get_frequency()
        self.offset = js8_msg.get_offset()
        self.snr = js8_msg.get_snr()

    def signal_reload(self, ui_area):
        status = Status()
        if ui_area == 'header':
            status.set_hdr_updated()
        elif ui_area == 'blog':
            status.set_blog_updated()
        elif ui_area == 'post_list':
            status.set_post_list_updated()
        elif ui_area == 'post_content':
            status.set_post_updated()
        elif ui_area == 'progress':
            status.set_progress_updated()

        notify_msg = GuiMessage()

        notify_msg.set_ts()
        notify_msg.set_req_ts(0)
        notify_msg.set_cmd('Notify')
        notify_msg.set_blog('')
        notify_msg.set_station('')
        notify_msg.set_frequency(0)
        notify_msg.set_post_id(0)
        notify_msg.set_post_date(0)
        notify_msg.set_op('reload')
        notify_msg.set_param(ui_area)
        notify_msg.set_rc(0)
        self.b2f_q.put(notify_msg)
        return

    def update_blog_list(self, blog: str, station: str, freq: int, post_id: int, post_date: float = 0):
        # do we have a blog entry for this blog at this station
        blog_table = DbTable('blog')
        results = blog_table.select(
            where=f"blog='{blog}' AND station='{station}' AND frequency={freq}",
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
                    where=f"blog='{blog}' AND station='{station}' AND frequency={freq}"
                )
            else:
                blog_table.update(
                    value_dictionary={
                        'last_seen_date': time.time()
                    },
                    where=f"blog='{blog}' AND station='{station}' AND frequency={freq}"
                )
        else:
            # no existing blog entry so create one
            blog_table.insert(
                row={'blog': blog, 'station': station, 'frequency': freq,
                     'snr': self.snr, 'latest_post_id': post_id,
                     'latest_post_date': post_date, 'last_seen_date': time.time(),
                     'is_selected': 0, 'info': ''}
            )
        self.signal_reload('blog')

    def process_announcement(self, req: list):
        # we need to support two formats of announcement
        # old:  callsign callsign blog_name post_id date_time
        # new:  callsign callsign post_id date_time

        status = Status()

        station = req[0]

        # if req[2] is an integer it must be the new style announcement
        try:
            announcement_post_id = int(req[2])
            blog = station
            announcement_post_date = time.mktime(
                time.strptime(
                    "20" + req[3] + "-" + req[4] + "-" + req[5] + " GMT", "%Y-%m-%d %Z"
                )
            )

        except ValueError:
            # must be an old style announcement
            blog = req[2]
            announcement_post_id = int(req[3])
            announcement_post_date = time.mktime(time.strptime(req[4] + " GMT", "%Y-%m-%d %Z"))

        self.update_blog_list(blog, station, status.radio_frequency, announcement_post_id, announcement_post_date)

    def process_listing(self, req: list, is_extended=False):
        status = Status()
        # the req list has source station [0], destination station [1],
        # + or - for good or bad response [2], the original command [3],
        # a post_id or post_date or list of dates [4], and list entries separated by \n character [5]

        directed_to = req[1]

        # push the data into the database
        rsp_lines = str(req[5]).split('\n')  # this is the list output
        for line in rsp_lines:
            if line == 'NO POSTS FOUND':
                self.title = line
            else:
                if is_extended:
                    details = re.findall(r"(\d+) - (\d{4}-\d{2}-\d{2}) - ([\S\s]+)", line)
                    self.post_id = int(details[0][0])
                    self.post_date = time.mktime(time.strptime(details[0][1], "%Y-%m-%d"))
                    self.title = details[0][2]
                else:
                    details = re.findall(r"(\d+) - ([\S\s]+)", line)
                    if len(details) > 0:
                        self.post_id = int(details[0][0])
                        self.title = details[0][1]
                    else:  # got something unexpected - just output it
                        self.rsp = rsp_lines[0]
                        self.title = f"{self.cmd} {rsp_lines[0]}"

            post_table = DbTable('post')
            # if we already have an entry for this post we only want to replace it
            # if this listing was directed_to this station

            db_values = post_table.select(
                where=f"blog='{self.blog}' AND post_id={self.post_id}",
                hdr_list=['body', 'is_selected']
            )

            if len(db_values) == 0:
                # Delete any existing entry and create a new one
                post_table.delete(
                    where=f"blog='{self.blog}' AND post_id={self.post_id}"
                )

                row = {
                    'qso_date': self.qso_date, 'blog': self.blog, 'station': self.station,
                    'directed_to': self.directed_to, 'frequency': self.frequency, 'offset': self.offset,
                    'cmd': self.cmd,
                    'post_id': self.post_id, 'post_date': self.post_date, 'title': self.title, 'body': '',
                    'is_selected': 0
                }
                post_table.insert(row)

            elif directed_to == status.callsign:
                # Delete any existing entry and create a new one
                post_table.delete(
                    where=f"blog='{self.blog}' AND post_id={self.post_id}"
                )

                row = {
                    'qso_date': self.qso_date, 'blog': self.blog, 'station': self.station,
                    'directed_to': self.directed_to, 'frequency': self.frequency, 'offset': self.offset,
                    'cmd': self.cmd,
                    'post_id': self.post_id, 'post_date': self.post_date, 'title': self.title,
                    'body': db_values[0]['body'], 'is_selected': db_values[0]['is_selected']
                }
                post_table.insert(row)

            self.signal_reload('post_list')
            self.signal_reload('post_content')
            self.update_blog_list(self.blog, self.station, status.radio_frequency, self.post_id, self.post_date)

    def process_extended(self, req: list):
        self.process_listing(req, True)

    def process_post(self, msg_fields: list):
        status = Status()

        # push the data into the database
        post_table = DbTable('post')

        # do we have the title for this blog
        self.post_id = int(msg_fields[4])
        db_values = post_table.select(
            where=f"blog='{self.blog}' AND post_id={self.post_id}",
            limit=1,
            hdr_list=['post_id']
        )

        if len(db_values) > 0:
            post_table.update(
                value_dictionary={'body': msg_fields[5]},
                where=f"blog='{self.blog}' AND post_id={self.post_id}"
            )
            # signal post table update
            status.set_post_updated()

        else:
            post_table.insert(
                row={
                    'qso_date': self.qso_date,
                    'blog': status.selected_blog,
                    'station': status.selected_station,
                    'directed_to': '',
                    'frequency': status.radio_frequency,
                    'offset': status.offset,
                    'cmd': 'G',
                    'post_id': self.post_id,
                    'post_date': 0.0,
                    'title': f"** {msg_fields[5][:20]}",
                    'body': msg_fields[5],
                    'is_selected': 0
                   },
            )
            # signal post table update
            status.set_post_list_updated()

    def process_weather(self, req: list):
        req.insert(4, 0)  # insert a dummy post_id into the request
        self.process_post(req)
        pass

    def process_info(self, msg_fields: list):
        status = Status()
        blog = msg_fields[0]
        info = msg_fields[3]

        # push the data into the database
        blog_table = DbTable('blog')

        # do we have the title for this blog
        db_values = blog_table.select(
            where=f"blog='{blog}' AND frequency={status.radio_frequency}",
            limit=1,
            hdr_list=['info']
        )

        if len(db_values) > 0:
            blog_table.update(
                value_dictionary={'info': info},
                where=f"blog='{self.blog}' AND frequency={status.radio_frequency}"
            )
            # signal post table update
            status.set_blog_updated()

    def parse_rx_message(self, mb_rsp_string: str):
        rsp_patterns = [
            {'exp': r"^([A-Z,0-9/]+): +(@MB) +(\d+) +(\d{2})(\d{2})(\d{2})",
             'proc': 'process_announcement'},  # new style announcement
            {'exp': r"^([A-Z,0-9/]+): +(@MB) +([A-Z,0-9/]+) +(\d+) +(\d{4}-\d{2}-\d{2})",
             'proc': 'process_announcement'},  # old style announcement
            {'exp': "^(\\S+): +(\\S+) +([+-])(L)([\\d,]*)~\n*([\\S\\s]+)", 'proc': 'process_listing'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(L)([\\dABC]*)~\n*([\\S\\s]+)", 'proc': 'process_listing'},
            {'exp': "^(\\S+): +(\\S+) +([+-])([LM][EG])([\\dABC]*)~\n*([\\S\\s]+)", 'proc': 'process_listing'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(E)([\\d,]*)~\n*([\\S\\s]+)", 'proc': 'process_extended'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(E)([\\dABC]*)~\n*([\\S\\s]+)", 'proc': 'process_extended'},
            {'exp': "^(\\S+): +(\\S+) +([+-])([EF][EG])([\\dABC]*)~\n*([\\S\\s]+)", 'proc': 'process_extended'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(G)(\\d+)~\n*([\\S\\s]+)", 'proc': 'process_post'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(WX)~\n*([\\S\\s]+)", 'proc': 'process_weather'},
            {'exp': "^(\\S+): +(\\S+) +(INFO) +([\\S\\s]+)", 'proc': 'process_info'},
        ]
        for entry in rsp_patterns:
            # try to match the request
            result = re.findall(entry['exp'], mb_rsp_string)
            if len(result) == 0:
                continue
            else:
                # the result is a list of tuples
                result = list(result[0])  # pull the 1st result out of the list and convert to a list
                self.station = result[0]
                # ToDo: the following line must be changed once we implement the blog namespace
                self.blog = result[0]
                # process if the result was positive
                if result[2] == '+':
                    self.cmd = f"{result[2]}{result[3]}{result[4]}~"
                    logger.info(self.cmd)
                    add_progress(self.cmd)
                    getattr(ServerMsgProcessors, entry['proc'])(self, result)

                elif result[1] == '@MB':
                    getattr(ServerMsgProcessors, entry['proc'])(self, result)
                    try:
                        progress_msg = f"{result[1]} {result[2]} {result[3]}{result[4]}{result[5]}"
                    except ValueError:
                        progress_msg = f"{result[1]} {result[2]} {result[3]}"
                    logger.info(progress_msg)
                    add_progress(progress_msg)

                elif result[2] == 'INFO':
                    getattr(ServerMsgProcessors, entry['proc'])(self, result)
                    progress_msg = f"{result[1]} {result[2]} {result[3]}"
                    logger.info(progress_msg)
                    add_progress(progress_msg)

                else:
                    self.mb_status.reload_status()
                    if result[1] == self.mb_status.callsign:  # we only need to show an error if this rsp was for us
                        error_msg = f"{result[2]}{result[3]}{result[4]}~"
                        logger.info(error_msg)
                        add_progress(error_msg)
                break


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
        status = Status()
        if ui_area == 'header':
            status.set_hdr_updated()
        elif ui_area == 'blog':
            status.set_blog_updated()
        elif ui_area == 'post_list':
            status.set_post_list_updated()
        elif ui_area == 'post':
            status.set_post_updated()

        notify_msg = GuiMessage()

        notify_msg.set_ts()
        notify_msg.set_req_ts(0)
        notify_msg.set_cmd('Notify')
        notify_msg.set_blog('')
        notify_msg.set_station('')
        notify_msg.set_frequency(0)
        notify_msg.set_post_id(0)
        notify_msg.set_post_date(0)
        notify_msg.set_op('reload')
        notify_msg.set_param(ui_area)
        notify_msg.set_rc(0)
        self.b2f_q.put(notify_msg)
        return

    # when we call this function, the post_id_list must contain post_ids in numerical order
    def get_post_from_server(self, req: GuiMessage):
        status = Status()  # we'll need status data a bit later

        # form a request to get the posts in the svr_request_list
        payload = f"G{req.post_id}~"
        logger.debug('comms: send: ' + str(payload))
        mblog_api_req = CommsMessage()

        mblog_api_req.set_ts(time.time())
        mblog_api_req.set_direction('tx')
        mblog_api_req.set_source(status.callsign)
        mblog_api_req.set_destination(req.blog)
        mblog_api_req.set_snr(0)
        mblog_api_req.set_blog(req.blog)
        mblog_api_req.set_typ('mb_req')
        mblog_api_req.set_target('mb_service')
        mblog_api_req.set_obj('service')
        mblog_api_req.set_payload(str(payload))
        self.comms_tx_q.put(mblog_api_req)

        return

    def get_list_via_cache(self, req: GuiMessage, post_id_list: list) -> None:
        blog = req.get_blog()
        station = req.get_station()

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
            status = Status()

            payload = f"E{posts_needed}~"
            logger.debug('comms: send: ' + str(payload))
            mblog_api_req = CommsMessage()

            mblog_api_req.set_ts(time.time())
            mblog_api_req.set_direction('tx')
            mblog_api_req.set_source(status.callsign)
            mblog_api_req.set_destination(station)
            mblog_api_req.set_snr(0)
            mblog_api_req.set_blog(blog)
            mblog_api_req.set_typ('mb_req')
            mblog_api_req.set_target('mb_service')
            mblog_api_req.set_obj('service')
            mblog_api_req.set_payload(str(payload))
            self.comms_tx_q.put(mblog_api_req)

        return

    def process_list_cmd(self, req: GuiMessage):
        settings = Settings()

        post_ids = []

        if req.get_op() == 'eq':
            post_ids.append(req.get_post_id())

        elif req.get_op() == 'gt':
            for i in range(settings.max_listing):
                post_ids.append(req.get_post_id() + 1 + i)

        elif req.get_op() == 'recent':
            # get the latest post id for this blog
            blog_obj = BlogInstanceFQ(req.get_blog(), req.get_blog(), req.get_frequency())
            latest_post_id, latest_post_date = blog_obj.get_latest_post_details()

            starting_post_id = max(latest_post_id - settings.max_listing + 1, 1)

            for i in range(starting_post_id, latest_post_id + 1):
                post_ids.append(i)

        elif req.get_op() == 'more':
            starting_post_id = max(req.get_post_id() - settings.max_listing, 1)

            for i in range(starting_post_id, req.get_post_id()):
                post_ids.append(i)

        if req.get_cmd() == 'E':
            # do we have any of the information in the cache
            self.get_list_via_cache(req, post_ids)
        elif req.get_cmd() == 'D':
            # get the listing info from the server
            status = Status()

            payload = f"E{req.get_post_id()}~"
            logger.debug('comms: send: ' + str(payload))
            mblog_api_req = CommsMessage()

            mblog_api_req.set_ts(time.time())
            mblog_api_req.set_direction('tx')
            mblog_api_req.set_source(status.callsign)
            mblog_api_req.set_destination(req.get_station())
            mblog_api_req.set_snr(0)
            mblog_api_req.set_blog(req.get_blog())
            mblog_api_req.set_typ('mb_req')
            mblog_api_req.set_target('mb_service')
            mblog_api_req.set_obj('service')
            mblog_api_req.set_payload(str(payload))
            self.comms_tx_q.put(mblog_api_req)

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
        status = Status()

        payload = f"{req.get_cmd()}"
        logger.debug('comms: send: ' + str(payload))
        mblog_api_req = CommsMessage()

        mblog_api_req.set_ts(time.time())
        mblog_api_req.set_direction('tx')
        mblog_api_req.set_source(status.callsign)
        mblog_api_req.set_destination('@MB')
        mblog_api_req.set_snr(0)
        mblog_api_req.set_blog('@MB')
        mblog_api_req.set_typ('mb_req')
        mblog_api_req.set_target('mb_service')
        mblog_api_req.set_obj('service')
        mblog_api_req.set_payload(str(payload))
        self.comms_tx_q.put(mblog_api_req)
        return

    def process_info_cmd(self, req: GuiMessage):
        status = Status()

        payload = f"INFO?"
        logger.debug('comms: send: ' + str(payload))
        mblog_api_req = CommsMessage()

        mblog_api_req.set_ts(time.time())
        mblog_api_req.set_direction('tx')
        mblog_api_req.set_source(status.callsign)
        mblog_api_req.set_destination(req.get_blog())
        mblog_api_req.set_snr(0)
        mblog_api_req.set_blog(req.get_blog())
        mblog_api_req.set_typ('mb_req')
        mblog_api_req.set_target('mb_service')
        mblog_api_req.set_obj('service')
        mblog_api_req.set_payload(str(payload))
        self.comms_tx_q.put(mblog_api_req)
        return

    def process_weather_cmd(self, req: GuiMessage):
        status = Status()

        payload = f"WX~"
        logger.debug('comms: send: ' + str(payload))
        mblog_api_req = CommsMessage()

        mblog_api_req.set_ts(time.time())
        mblog_api_req.set_direction('tx')
        mblog_api_req.set_source(status.callsign)
        mblog_api_req.set_destination(req.get_station())
        mblog_api_req.set_snr(0)
        mblog_api_req.set_blog(req.get_blog())
        mblog_api_req.set_typ('mb_req')
        mblog_api_req.set_target('mb_service')
        mblog_api_req.set_obj('service')
        mblog_api_req.set_payload(str(payload))
        self.comms_tx_q.put(mblog_api_req)
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
        # signal to the comms driver that the frequency must be changed
        comms_sig = CommsMessage()
        comms_sig.set_ts(time.time())
        comms_sig.set_direction('tx')
        comms_sig.set_typ('control')
        comms_sig.set_target('set')
        comms_sig.set_obj('radio_frequency')
        comms_sig.set_payload(freq)
        self.comms_tx_q.put(comms_sig)

    def set_hdr_callsign(self, callsign: str):
        s = DbTable('status')
        s.update(
            where=None, value_dictionary={
                'callsign': callsign
            }
        )

        self.signal_reload('header')

    def select_blog(self, req: GuiMessage):

        blog = req.get_blog()
        station = req.get_station()
        frequency = req.get_frequency()

        if len(blog) > 0:
            if len(station) > 0:
                s = DbTable('status')
                s.update(
                    where=None, value_dictionary={
                        'selected_blog': blog,
                        'selected_station': station,
                        'radio_frequency': frequency,
                        'user_frequency': frequency
                    }
                )

                # update the selected row
                b = DbTable('blog')
                b.update(where=None, value_dictionary={'is_selected': 0})
                b.update(where=f"blog='{blog}' AND station='{station}' AND frequency={frequency}",
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

                # send OK back to the frontend
                rsp = GuiMessage()
                rsp.clone_msg(req)
                rsp.set_blog(blog)
                rsp.set_rc(0)
                self.b2f_q.put(rsp)

    def process_set_cmd(self, req: GuiMessage):

        if len(req.get_blog()) > 0:
            self.select_blog(req)
        elif req.get_frequency() > 0:
            self.set_rig_frequency(req.get_frequency())

    def process_config_cmd(self, msg: GuiMessage):
        pass

    def process_scan_cmd(self, msg: GuiMessage):
        pass

    def preprocess(self, msg_object: GuiMessage):
        command = msg_object.get_cmd()
        msg_prefix = "BeProcessor:preprocess: "

        if command == 'X':
            # we have to give the comms interface a kick to get its thread to shut down
            comms_sig = CommsMessage()
            comms_sig.set_ts(time.time())
            comms_sig.set_direction('tx')
            comms_sig.set_typ('control')
            comms_sig.set_target('set')
            comms_sig.set_obj('exit')
            self.comms_tx_q.put(comms_sig)

            logger.info(f"{msg_prefix}{command}")
            add_progress(command)
            exit(0)

        elif command == 'L':
            # Get abbreviated list
            process_msg = f"{command}{msg_object.get_op()}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_list_cmd(msg_object)

        elif command == 'D':
            # Get full list details not using the cache
            process_msg = f"{command}{msg_object.get_op()}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_extended_cmd(msg_object)

        elif command == 'E':
            # Get full list details using the cache
            process_msg = f"{command}{msg_object.get_op()}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_extended_cmd(msg_object)

        elif command == 'F':
            # Fetch post(s)
            process_msg = f"{command}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_fetch_cmd(msg_object)
            self.signal_reload('post')

        elif command == 'G':
            # Get post(s)
            process_msg = f"{command}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.get_post_from_server(msg_object)

        elif command == 'R':
            # Refresh a post (results in sending a Get to the server)
            process_msg = f"{command}{msg_object.get_post_id()}~"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_refresh_cmd(msg_object)

        elif command == 'I':
            # Get information from the server
            process_msg = f"INFO?"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_info_cmd(msg_object)

        elif command == 'S':
            # Switch to a blog (internal - no server command is sent)
            process_msg = f"{command}"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_set_cmd(msg_object)

        elif command == 'C':
            # Change the config - not implemented
            process_msg = f"{command}"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_config_cmd(msg_object)

        elif command == 'P':
            # Initiate a Scan - not implemented
            process_msg = f"{command}"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_scan_cmd(msg_object)

        elif command == 'Q':
            # Query command to elicit an announcement from all MB servers
            process_msg = f"{command}"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_query_cmd(msg_object)

        elif command == 'WX':
            # Request a weather report - results in G0~ to the server
            process_msg = f"{command}"
            logger.info(f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_weather_cmd(msg_object)

        self.signal_reload('post_list')
        self.signal_reload('post')

    def process_mb_rsp(self, comms_msg: CommsMessage):
        processor = ServerMsgProcessors(comms_msg, self.b2f_q)
        # check to see if this is a listing, extended listing or post and process accordingly
        processor.parse_rx_message(comms_msg.get_payload())

        self.signal_reload('post_list')

    def process_mb_notify(self, comms_msg: CommsMessage):
        # ToDo: we should only insert an entry in qso if we don't have an entry already
        processor = ServerMsgProcessors(comms_msg, self.b2f_q)
        # check to see if this is a listing, extended listing or post and process accordingly
        processor.parse_rx_message(comms_msg.get_payload())

        self.signal_reload('blog')
        pass

    def process_status_radio_frequency(self, comms_msg: CommsMessage):
        self.set_hdr_freq(comms_msg.get_frequency())

    def process_status_offset(self, comms_msg: CommsMessage):
        self.set_hdr_offset(comms_msg.get_offset())

    def process_status_callsign(self, comms_msg: CommsMessage):
        self.set_hdr_callsign(comms_msg.get_payload())

    def process_comms_rx(self, comms_msg: CommsMessage):
        if comms_msg.get_target() == 'frontend':
            notify_msg = GuiMessage()

            notify_msg.set_ts()
            notify_msg.set_req_ts(0)
            notify_msg.set_cmd('Notify')
            notify_msg.set_blog('')
            notify_msg.set_station('')
            notify_msg.set_frequency(0)
            notify_msg.set_post_id(0)
            notify_msg.set_post_date(0)
            notify_msg.set_op(comms_msg.get_payload())
            notify_msg.set_param('')
            notify_msg.set_rc(0)
            self.b2f_q.put(notify_msg)

        elif comms_msg.get_typ() == 'mb_rsp':
            self.process_mb_rsp(comms_msg)
        elif comms_msg.get_typ() == 'mb_notify':
            self.process_mb_notify(comms_msg)
        elif comms_msg.get_typ() == 'control' and comms_msg.get_target() == 'status'\
                and comms_msg.get_obj() == 'radio_frequency':
            self.process_status_radio_frequency(comms_msg)
        elif comms_msg.get_typ() == 'control' and comms_msg.get_target() == 'status'\
                and comms_msg.get_obj() == 'offset':
            self.process_status_offset(comms_msg)
        elif comms_msg.get_typ() == 'control' and comms_msg.get_target() == 'status'\
                and comms_msg.get_obj() == 'callsign':
            self.process_status_callsign(comms_msg)

        pass

    def check_for_msg(self):
        # check for messages from the frontend
        try:
            fe_msg: GuiMessage = self.f2b_q.get(block=False)
            if fe_msg:
                logger.debug(f"{fe_msg.cmd}")
                self.preprocess(fe_msg)
                self.f2b_q.task_done()
        except queue.Empty:
            pass  # nothing on the queue - do nothing

        # check for messages from the comms driver
        try:
            comms_rx: CommsMessage = self.comms_rx_q.get(block=True, timeout=0.1)  # if no msg waiting, throw an except
            logger.debug(f"{comms_rx.payload}")
            self.process_comms_rx(comms_rx)
            self.comms_rx_q.task_done()
        except queue.Empty:
            pass


class Backend:

    proc = None  # for backend processor

    def __init__(self, f2b_q: queue.Queue, b2f_q: queue.Queue, comms_tx_q: queue.Queue, comms_rx_q: queue.Queue):
        self.proc = BeProcessor(f2b_q, b2f_q, comms_tx_q, comms_rx_q)
        pass

    def backend_loop(self):
        while True:
            # check for f2b message and process
            self.proc.check_for_msg()
            time.sleep(0.2)  # we need this else the backend thread hogs the cpu
