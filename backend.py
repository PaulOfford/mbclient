import queue
import re

from settings import *
from message_q import *
from logging import *


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


class ServerMsgProcessors:

    qso_fields = ['qso_date', 'type', 'blog', 'station', 'directed_to', 'frequency',
                  'offset', 'cmd', 'rsp', 'post_id', 'post_date', 'title', 'body']

    mb_status = None
    qso_date = 0
    blog = ''
    station = ''
    directed_to = ''
    frequency = 0
    offset = 0
    snr = 0
    cmd = ''
    rsp = ''
    post_id = 0
    post_date = 0
    title = ''
    body = ''

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
        elif ui_area == 'post_content':
            status.set_post_content_updated()
        elif ui_area == 'post_list':
            status.set_post_list_updated()
        elif ui_area == 'cli':
            status.set_cli_updated()
        elif ui_area == 'blogs':
            status.set_blogs_updated()

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

    def update_blog_list(self, blog: str, station: str, post_id: int, post_date: float = 0):
        # do we have a blog entry for this blog at this station
        blogs_table = DbTable('blogs')
        results = blogs_table.select(
            where=f"blog='{blog}' AND station='{station}' AND frequency={self.frequency}",
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
                blogs_table.update(
                    value_dictionary={
                        'latest_post_id': post_id,
                        'latest_post_date': post_date,
                        'last_seen_date': time.time()
                    },
                    where=f"blog='{blog}' AND station='{station}' AND frequency={self.frequency}"
                )
            else:
                blogs_table.update(
                    value_dictionary={
                        'last_seen_date': time.time()
                    },
                    where=f"blog='{blog}' AND station='{station}' AND frequency={self.frequency}"
                )
        else:
            # no existing blogs entry so create one
            blogs_table.insert(
                row={'blog': blog, 'station': station, 'frequency': self.frequency,
                     'snr': self.snr, 'capabilities': 'LEG', 'post_id': post_id,
                     'latest_post_date': post_date, 'last_seen_date': time.time(),
                     'is_selected': 0}
            )
        self.signal_reload('blogs')

    def process_announcement(self, req: list):
        # we need to support two formats of announcement
        # old:  callsign callsign blog_name post_id date_time
        # new:  callsign callsign post_id date_time

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

        self.update_blog_list(blog, station, announcement_post_id, announcement_post_date)

    def process_listing(self, req: list, is_extended=False):

        # the req list has source station [0], destination station [1],
        # + or - for good or bad response [2], the original command [3],
        # a post_id or post_date or list of dates [4], and list entries separated by \n character [5]

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
            # Update an existing QSO entry or create a new one
            row = {'qso_date': self.qso_date, 'type': 'listing', 'blog': self.blog, 'station': self.station,
                   'directed_to': self.directed_to, 'frequency': self.frequency, 'offset': self.offset, 'cmd': self.cmd,
                   'rsp': self.rsp, 'post_id': self.post_id, 'post_date': self.post_date, 'title': self.title,
                   'body': self.body}
            post_table.insert(row)

            self.signal_reload('post_list')
            self.update_blog_list(self.blog, self.station, self.post_id, self.post_date)

    def process_extended(self, req: list):
        self.process_listing(req, True)

    def process_post(self, req: list):
        status = Status()

        # push the data into the database
        post_table = DbTable('post')

        # do we have the title for this blog
        self.post_id = int(req[4])
        db_values = post_table.select(where=f"blog='{self.blog}' AND post_id={self.post_id}",
                                     limit=1, hdr_list=['post_id'])

        if len(db_values) > 0:
            post_table.update(
                value_dictionary={'body': req[5]},
                where=f"blog='{self.blog}' AND post_id={self.post_id}"
            )

        else:
            row = {'qso_date': self.qso_date, 'type': 'post',
                   'blog': status.selected_blog, 'station': status.selected_station,
                   'frequency': status.radio_frequency, 'offset': status.offset,
                   'body': req[5]}
            post_table.insert(row)

    def process_weather(self, req: list):
        req.insert(4, 0)  # insert a dummy post_id into the request
        self.process_post(req)
        pass

    def parse_rx_message(self, mb_rsp_string: str):
        rsp_patterns = [
            {'exp': "^([A-Z,0-9\/]+): +(@MB) +(\\d+) +(\\d{2})(\\d{2})(\\d{2})",
             'proc': 'process_announcement'},  # new style announcement
            {'exp': "^([A-Z,0-9\/]+): +(@MB) +([A-Z,0-9\/]+) +(\\d+) +(\\d{4}-\\d{2}-\\d{2})",
             'proc': 'process_announcement'},  # old style announcement
            {'exp': "^(\\S+): +(\\S+) +([+-])(L)([\\d,]*)~\n*([\\S\\s]+)", 'proc': 'process_listing'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(L)([\\dABC]*)~\n*([\\S\\s]+)", 'proc': 'process_listing'},
            {'exp': "^(\\S+): +(\\S+) +([+-])([LM][EG])([\\dABC]*)~\n*([\\S\\s]+)", 'proc': 'process_listing'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(E)([\\d,]*)~\n*([\\S\\s]+)", 'proc': 'process_extended'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(E)([\\dABC]*)~\n*([\\S\\s]+)", 'proc': 'process_extended'},
            {'exp': "^(\\S+): +(\\S+) +([+-])([EF][EG])([\\dABC]*)~\n*([\\S\\s]+)", 'proc': 'process_extended'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(G)(\\d+)~\n*([\\S\\s]+)", 'proc': 'process_post'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(WX)~\n*([\\S\\s]+)", 'proc': 'process_weather'},
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
                    logmsg(1, self.cmd)
                    add_progress(self.cmd)
                    getattr(ServerMsgProcessors, entry['proc'])(self, result)
                elif result[1] == '@MB':
                    getattr(ServerMsgProcessors, entry['proc'])(self, result)
                    progress_msg = f"{result[1]} {result[2]} {result[3]}"
                    logmsg(1, progress_msg)
                    add_progress(progress_msg)
                else:
                    self.mb_status.reload_status()
                    if result[1] == self.mb_status.callsign:  # we only need to show an error if this rsp was for us
                        error_msg = f"{result[2]}{result[3]}{result[4]}~"
                        logmsg(1, error_msg)
                        add_progress(error_msg)
                break


class BeProcessor:

    qso_fields = ['qso_date', 'type', 'blog', 'station', 'directed_to', 'frequency',
                  'offset', 'cmd', 'rsp', 'post_id', 'post_date', 'title', 'body']

    f2b_q = None
    b2f_q = None
    comms_tx_q = None
    comms_rx_q = None
    status = Status()

    def __init__(self, f2b_q: queue.Queue, b2f_q: queue.Queue, comms_tx_q: queue.Queue, comms_rx_q: queue.Queue):
        self.f2b_q = f2b_q
        self.b2f_q = b2f_q
        self.comms_tx_q = comms_tx_q
        self.comms_rx_q = comms_rx_q

    def signal_reload(self, ui_area):
        status = Status()
        if ui_area == 'header':
            status.set_hdr_updated()
        elif ui_area == 'blogs':
            status.set_blogs_updated()
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
    def get_post_via_cache(self, req: GuiMessage, blog: str, post_id: int):
        self.status.reload_status()  # we'll need status data a bit later

        # initialise some values
        post_date = 0.0
        subject = ''
        body = ''

        # check if the data is in the cache
        post_fields = ['post_id', 'post_date', 'title', 'body']

        post_table = DbTable('post')
        db_values = post_table.select(
            where=f"blog='{blog}' and post_id={post_id} and length(body) > 0",
            hdr_list=self.qso_fields
        )

        if len(db_values) > 0:
            # we have an entry in the cache
            post_date = db_values[0]['post_date']
            subject = db_values[0]['title']
            body = db_values[0]['body']
            pass

        else:
            # form a request to get the posts in the svr_request_list
            payload = f"G{post_id}~"
            logmsg(3, 'comms: send: ' + str(payload))
            mblog_api_req = CommsMessage()

            mblog_api_req.set_ts(time.time())
            mblog_api_req.set_direction('tx')
            mblog_api_req.set_source(self.status.callsign)
            mblog_api_req.set_destination(blog)  # ToDo: change once we implement blog namespace
            mblog_api_req.set_snr(0)
            mblog_api_req.set_blog(blog)
            mblog_api_req.set_typ('mb_req')
            mblog_api_req.set_target('mb_service')
            mblog_api_req.set_obj('service')
            mblog_api_req.set_payload(str(payload))
            self.comms_tx_q.put(mblog_api_req)

        return blog, post_id, post_date, subject, body

    def get_list_via_cache(self, req: GuiMessage, post_id_list: list):
        # ToDo: this isn't working - it always sends a request to the server
        blog = req.get_blog()
        station = req.get_station()
        cmd = req.get_cmd()

        svr_request_list = []  # this is a list of post_ids we will need to request from the server

        # set up the list of dictionaries fo the results
        init_vals = {'cmd': '', 'post_id': 0, 'has_entry': False, 'date': 0, 'title': '', 'body': ''}

        return_values = [{} for _ in range(len(post_id_list))]

        for i, _ in enumerate(return_values):
            return_values[i] = init_vals.copy()

        range_start = post_id_list[0]
        range_end = post_id_list[len(post_id_list) - 1]

        # form a sql WHERE clause based on command
        where_clause = f"blog='{blog}' and post_id>={range_start} and post_id<={range_end}"

        if cmd == 'L':
            where_clause += " and title<>''"
        elif cmd == 'E':
            where_clause += " and title<>'' and post_date>0"
        elif cmd == 'G':
            where_clause += " and body<>''"

        post_table = DbTable('post')
        db_values = post_table.select(
            where=where_clause,
            group_by='post_id',
            order_by='post_id, body, title', desc=True,
            hdr_list=self.qso_fields
        )

        self.status.reload_status()  # we'll need status data a bit later

        for i, value in enumerate(return_values):
            value.update({'post_id': post_id_list[i]})
            for row in db_values:
                if value['post_id'] == int(row['post_id']):
                    value.update(
                        {'cmd': req.cli_input, 'has_entry': True,
                         'date': row['post_date'], 'title': row['title'], 'body': row['body']}
                    )
                    row['qso_date'] = time.time()
                    row['directed_to'] = self.status.callsign
                    row['cmd'] = req.cli_input
                    break

            if not value['has_entry']:
                svr_request_list.append(value['post_id'])

        # if we have all the return values (has_entry is true), we can return them
        if len(svr_request_list) == 0:
            return return_values

        posts_needed = ''
        for post in svr_request_list:
            if len(posts_needed) > 0:
                posts_needed += ','
            posts_needed += str(post)

        # form a request to get the posts in the svr_request_list
        payload = f"{cmd}{posts_needed}~"
        logmsg(3, 'comms: send: ' + str(payload))
        mblog_api_req = CommsMessage()

        mblog_api_req.set_ts(time.time())
        mblog_api_req.set_direction('tx')
        mblog_api_req.set_source(self.status.callsign)
        mblog_api_req.set_destination(station)  # ToDo: change once we implement blog namespace
        mblog_api_req.set_snr(0)
        mblog_api_req.set_blog(blog)
        mblog_api_req.set_typ('mb_req')
        mblog_api_req.set_target('mb_service')
        mblog_api_req.set_obj('service')
        mblog_api_req.set_payload(str(payload))
        self.comms_tx_q.put(mblog_api_req)

        return return_values

    @staticmethod
    def get_posts_tail(blog: str, station: str):
        fields = ['latest_post_id', 'latest_post_date']

        blogs_table = DbTable('blogs')
        db_values = blogs_table.select(order_by='latest_post_id', desc=True, limit=1,
                                       where=f"blog='{blog}' and station='{station}'", hdr_list=fields)
        return db_values

    def process_list_cmd(self, req: GuiMessage):
        # If the request is to list based on a date or dates, we need to go to the server
        # because we have no way of knowing if we have all posts with a certain date.
        # If the request is a TAIL listing, we need to get the latest post number from the
        # blogs table as the range end, subtract from it the max_listing value to get a range start
        # and then get everything in that range.
        # If the request is to list a specific post by post id, simply check the cache for that.

        if req.get_post_date() > 0:
            compressed_date = compress_date(req.get_post_date())

            if req.cmd == 'L':
                api_cmd = 'M'
            elif req.cmd == 'E':
                api_cmd = 'F'
            else:
                api_cmd = ''

            if req.get_op() == 'eq':
                api_cmd += 'E'
            elif req.get_op() == 'gt':
                api_cmd += 'G'

            payload = f"{api_cmd}{compressed_date}~"
            logmsg(3, 'comms: send: ' + str(payload))
            mblog_api_req = CommsMessage()

            mblog_api_req.set_ts(time.time())
            mblog_api_req.set_direction('tx')
            mblog_api_req.set_source(self.status.callsign)
            mblog_api_req.set_destination(req.get_station())
            mblog_api_req.set_snr(0)
            mblog_api_req.set_blog(req.get_blog())
            mblog_api_req.set_typ('mb_req')
            mblog_api_req.set_target('mb_service')
            mblog_api_req.set_obj('service')
            mblog_api_req.set_payload(str(payload))
            self.comms_tx_q.put(mblog_api_req)

            return

        post_ids = []

        if req.get_op() == 'eq':
            post_ids.append(req.get_post_id())
        elif req.get_op() == 'gt':
            for i in range(settings.max_listing):
                post_ids.append(req.get_post_id() + 1 + i)
        elif req.get_op() == 'tail':
            # get the latest post id for this blog
            latest_post = self.get_posts_tail(req.get_blog(), req.get_station())

            for i in range(
                    latest_post[0]['latest_post_id'] - settings.max_listing + 1,
                    latest_post[0]['latest_post_id'] + 1
            ):
                post_ids.append(i)

        # do we have any of the information in the cache
        self.get_list_via_cache(req, post_ids)

        # get the frontend to reload the Post List
        self.signal_reload('post_list')
        return

    def process_extended_cmd(self, req: GuiMessage):
        self.process_list_cmd(req)

    def process_get_cmd(self, req: GuiMessage):
        blog = req.get_blog()
        post_id = req.get_post_id()

        # set this as the selected post
        post_table = DbTable('post')
        post_table.update(where=None, value_dictionary={'is_selected': 0})
        post_table.update(where=f"post_id={post_id}",
                 value_dictionary={'is_selected': 1})

        self.status.set_current_post(post_id)

        self.get_post_via_cache(req, blog, post_id)

        self.signal_reload('post')
        return

    def process_refresh_cmd(self, req: GuiMessage):
        post_id = req.get_post_id()
        # remove the post from the cache
        q = DbTable('post')
        where_clause = f"type='post' AND blog='{req.get_blog()}' AND post_id={post_id} AND body IS NOT NULL"
        q.delete(where=where_clause)

        # now we've deleted the cache entry, we can process as though it were a GET
        req.cmd = 'G'
        self.process_get_cmd(req)
        return

    def process_query_cmd(self, req: GuiMessage):
        payload = f"Q"
        logmsg(3, 'comms: send: ' + str(payload))
        mblog_api_req = CommsMessage()

        mblog_api_req.set_ts(time.time())
        mblog_api_req.set_direction('tx')
        mblog_api_req.set_source(self.status.callsign)
        mblog_api_req.set_destination('@MB')
        mblog_api_req.set_snr(0)
        mblog_api_req.set_blog('@MB')
        mblog_api_req.set_typ('mb_req')
        mblog_api_req.set_target('mb_service')
        mblog_api_req.set_obj('service')
        mblog_api_req.set_payload(str(payload))
        self.comms_tx_q.put(mblog_api_req)
        return

    def process_weather_cmd(self, req: GuiMessage):
        payload = f"WX~"
        logmsg(3, 'comms: send: ' + str(payload))
        mblog_api_req = CommsMessage()

        mblog_api_req.set_ts(time.time())
        mblog_api_req.set_direction('tx')
        mblog_api_req.set_source(self.status.callsign)
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

    def process_info_cmd(self, req: GuiMessage):
        pass

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
                b = DbTable('blogs')
                b.update(where=None, value_dictionary={'is_selected': 0})
                b.update(where=f"blog='{blog}' AND station='{station}' AND frequency={frequency}",
                         value_dictionary={'is_selected': 1})

                s.update(
                    where=None,
                    value_dictionary={
                        'hdr_updated': time.time(),
                        'cli_updated': time.time(),
                        'blogs_updated': time.time()
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
            logmsg(1, f"{msg_prefix}{command}")
            add_progress(command)
            exit(0)
        elif command == 'L':
            # Get abbreviated list
            process_msg = f"{command}{msg_object.get_op()}{msg_object.get_post_id()}~"
            logmsg(1, f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_list_cmd(msg_object)
        elif command == 'E':
            # Get full list details
            process_msg = f"{command}{msg_object.get_op()}{msg_object.get_post_id()}~"
            logmsg(1, f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_extended_cmd(msg_object)
        elif command == 'G':
            # Get post(s)
            process_msg = f"{command}{msg_object.get_post_id()}~"
            logmsg(1, f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_get_cmd(msg_object)
        elif command == 'R':
            # Refresh a post (results in sending a Get to the server)
            process_msg = f"{command}{msg_object.get_post_id()}~"
            logmsg(1, f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_refresh_cmd(msg_object)
        elif command == 'I':
            # Get information from the server
            process_msg = f"{command}~"
            logmsg(1, f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_info_cmd(msg_object)
        elif command == 'S':
            # Switch to a blog (internal - no server command is sent)
            process_msg = f"{command}"
            logmsg(1, f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_set_cmd(msg_object)
        elif command == 'C':
            # Change the config - not implemented
            process_msg = f"{command}"
            logmsg(1, f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_config_cmd(msg_object)
        elif command == 'P':
            # Initiate a Scan - not implemented
            process_msg = f"{command}"
            logmsg(1, f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_scan_cmd(msg_object)
        elif command == 'Q':
            # Query command to elicit an announcement from all MB servers
            process_msg = f"{command}"
            logmsg(1, f"{msg_prefix}{process_msg}")
            add_progress(process_msg)
            self.process_query_cmd(msg_object)
        elif command == 'WX':
            # Request a weather report - results in G0~ to the server
            process_msg = f"{command}"
            logmsg(1, f"{msg_prefix}{process_msg}")
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

        self.signal_reload('blogs')
        pass

    def process_status_radio_frequency(self, comms_msg: CommsMessage):
        self.set_hdr_freq(comms_msg.get_frequency())

    def process_status_offset(self, comms_msg: CommsMessage):
        self.set_hdr_offset(comms_msg.get_offset())

    def process_status_callsign(self, comms_msg: CommsMessage):
        self.set_hdr_callsign(comms_msg.get_payload())

    def process_comms_rx(self, comms_msg: CommsMessage):
        if comms_msg.get_typ() == 'mb_rsp':
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
                logging.logmsg(3, f"backend: {fe_msg.cmd}")
                self.preprocess(fe_msg)
                self.f2b_q.task_done()
        except queue.Empty:
            pass  # nothing on the queue - do nothing

        # check for messages from the comms driver
        try:
            comms_rx: CommsMessage = self.comms_rx_q.get(block=True, timeout=0.1)  # if no msg waiting, throw an except
            logging.logmsg(3, f"backend: {comms_rx.payload}")
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
