import queue
import re

from settings import *
from message_q import *
from logging import *


class MbRspProcessors:

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
        elif ui_area == 'latest':
            status.set_latest_updated()
        elif ui_area == 'qso':
            status.set_qso_updated()
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
            where=f"blog='{blog}' AND station='{station}'",
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
                    where=f"blog='{blog}' AND station='{station}'"
                )
            else:
                blogs_table.update(
                    value_dictionary={
                        'last_seen_date': time.time()
                    },
                    where=f"blog='{blog}' AND station='{station}'"
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

    def qso_append_error(self, cli_input: str, rsp_text: str):
        self.mb_status.reload_status()
        qso_table = DbTable('qso')
        db_values = qso_table.select(limit=1, hdr_list=self.qso_fields)
        for row in db_values:
            row['qso_date'] = self.qso_date
            row['type'] = 'cmd'
            row['blog'] = self.blog
            row['station'] = self.station
            row['directed_to'] = self.directed_to
            row['frequency'] = self.frequency
            row['offset'] = self.offset
            row['cmd'] = cli_input
            row['rsp'] = rsp_text
            row['post_id'] = 0
            row['post_date'] = 0
            row['title'] = ''
            row['body'] = ''
            qso_table.insert(row)
        self.signal_reload('qso')

    def process_announcement(self, req: list):
        station = req[0]
        blog = req[2]
        announcement_post_id = int(req[3])
        announcement_post_date = time.mktime(time.strptime(req[4], "%Y-%m-%d"))

        self.update_blog_list(blog, station, announcement_post_id, announcement_post_date)

    def process_listing(self, req: list, is_extended=False):

        # the req list has source station [0], destination station [1],
        # + or - for good or bad response [2], the original command [3],
        # a post_id or post_date or list of dates [4], and list entries separated by \n character [5]

        # push the data into the database
        rsp_lines = str(req[5]).split('\n')  # this is the list output
        for line in rsp_lines:
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
            qso_table = DbTable('qso')
            db_values = qso_table.select(limit=1, hdr_list=self.qso_fields)
            for row in db_values:
                row['qso_date'] = self.qso_date
                row['type'] = 'listing'
                row['blog'] = self.blog
                row['station'] = self.station
                row['directed_to'] = self.directed_to
                row['frequency'] = self.frequency
                row['offset'] = self.offset
                row['cmd'] = self.cmd
                row['rsp'] = self.rsp
                row['post_id'] = self.post_id
                row['post_date'] = self.post_date
                row['title'] = self.title
                row['body'] = self.body
                qso_table.insert(row)

            self.signal_reload('qso')
            self.update_blog_list(self.blog, self.station, self.post_id, self.post_date)

    def process_extended(self, req: list):
        self.process_listing(req, True)

    def process_post(self, req: list):
        # push the data into the database
        qso_table = DbTable('qso')

        # do we have the title for this blog
        self.post_id = int(req[4])
        db_values = qso_table.select(where=f"blog='{self.blog}' AND post_id={self.post_id} AND title IS NOT ''",
                                     limit=1, hdr_list=['title'])
        for row in db_values:
            self.title = row['title']

        # do we have the date for this blog
        self.post_id = int(req[4])
        db_values = qso_table.select(where=f"blog='{self.blog}' AND post_id={self.post_id} AND post_date > 0",
                                     limit=1, hdr_list=['post_date'])
        for row in db_values:
            self.title = int(row['post_date'])

        db_values = qso_table.select(limit=1, hdr_list=self.qso_fields)
        for row in db_values:
            row['qso_date'] = self.qso_date
            row['type'] = 'post'
            row['blog'] = self.blog
            row['station'] = self.station
            row['directed_to'] = self.directed_to
            row['frequency'] = self.frequency
            row['offset'] = self.offset
            row['cmd'] = f'{req[3]}{req[4]}~'
            row['rsp'] = self.rsp
            row['post_id'] = int(req[4])
            row['post_date'] = 0
            row['title'] = ''
            row['body'] = req[5]
            qso_table.insert(row)
        # notify = B2fMessage(self.b2f_q)
        # notify.signal_reload('qso')

    def parse_rx_message(self, mb_rsp_string: str):
        rsp_patterns = [
            {'exp': "^([A-Z,0-9]+): +(@)MB +([A-Z,0-9]*) +(\\d+) +(\\d{4}-\\d{2}-\\d{2})",
             'proc': 'process_announcement'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(L)([\\d,]*)~\n*([\\S\\s]+)", 'proc': 'process_listing'},
            {'exp': "^(\\S+): +(\\S+) +([+-])([LM][EG])(\\d*)~\n*([\\S\\s]+)", 'proc': 'process_listing'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(E)([\\d,]*)~\n*([\\S\\s]+)", 'proc': 'process_extended'},
            {'exp': "^(\\S+): +(\\S+) +([+-])([EF][EG])(\\d*)~\n*([\\S\\s]+)", 'proc': 'process_extended'},
            {'exp': "^(\\S+): +(\\S+) +([+-])(G)(\\d+)~\n*([\\S\\s]+)", 'proc': 'process_post'}
        ]
        for entry in rsp_patterns:
            # try to match the request
            result = re.findall(entry['exp'], mb_rsp_string)
            if len(result) == 0:
                continue
            else:
                result = result[0]  # pull the result out of the list
                self.station = result[0]
                # ToDo: the following line must be changed once we implement the blog namespace
                self.blog = result[0]
                # process if the result was positive
                if result[2] == '+':
                    self.cmd = f"{result[2]}{result[3]}{result[4]}~"
                    getattr(MbRspProcessors, entry['proc'])(self, result)
                elif result[1] == '@':
                    getattr(MbRspProcessors, entry['proc'])(self, result)
                else:
                    self.mb_status.reload_status()
                    if result[1] == self.mb_status.callsign:  # we only need to show an error if this rsp was for us
                        self.qso_append_error(f"{result[2]}{result[3]}{result[4]}~", f"{result[5]}")
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
        elif ui_area == 'latest':
            status.set_latest_updated()
        elif ui_area == 'qso':
            status.set_qso_updated()
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

    def qso_append_cli_input(self, msg_object: GuiMessage):

        row = {}

        self.status.reload_status()

        row['qso_date'] = time.time()
        row['type'] = 'cmd'
        row['blog'] = msg_object.get_blog()
        row['station'] = msg_object.get_station()
        row['directed_to'] = self.status.callsign
        row['frequency'] = self.status.user_frequency
        row['offset'] = self.status.offset
        row['cmd'] = msg_object.get_cli_input()
        row['rsp'] = ''
        row['post_id'] = msg_object.get_post_id()
        row['post_date'] = msg_object.get_post_date()
        row['title'] = ''
        row['body'] = ''

        qso_table = DbTable('qso')
        qso_table.insert(row)

        self.signal_reload('qso')

    def qso_append_progress(self, blog, station, cli_input: str, rsp_text: str):
        self.status.reload_status()
        qso_table = DbTable('qso')
        db_values = qso_table.select(limit=1, hdr_list=self.qso_fields)
        for row in db_values:
            row['qso_date'] = time.time()
            row['type'] = 'progress'
            row['blog'] = blog
            row['station'] = station
            row['directed_to'] = self.status.callsign
            row['frequency'] = self.status.user_frequency
            row['offset'] = self.status.offset
            row['cmd'] = cli_input
            row['rsp'] = rsp_text
            row['post_id'] = 0
            row['post_date'] = 0
            row['title'] = ''
            row['body'] = ''
            qso_table.insert(row)

        self.signal_reload('qso')

    # when we call this function, the post_id_list must contain post_ids in numerical order
    def get_posts_via_cache(self, req: GuiMessage, post_id_list: list):

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

        qso_table = DbTable('qso')
        db_values = qso_table.select(
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
                    qso_table.insert(row)
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
        self.qso_append_progress(blog, station, 'Requesting details from the server for: ', f"{svr_request_list}")

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
        self.get_posts_via_cache(req, post_ids)

        # get the frontend to reload the qso box
        self.signal_reload('qso')
        return

    def process_extended_cmd(self, req: GuiMessage):
        self.process_list_cmd(req)

    def process_get_cmd(self, req: GuiMessage):
        post_ids = [req.get_post_id()]
        self.get_posts_via_cache(req, post_ids)

        self.signal_reload('qso')
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
                b.update(where=f"blog='{blog}' AND station='{station}'", value_dictionary={'is_selected': 1})

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
            self.qso_append_cli_input(req)
        elif req.get_frequency() > 0:
            self.set_rig_frequency(req.get_frequency())

    def process_config_cmd(self, msg: GuiMessage):
        pass

    def process_scan_cmd(self, msg: GuiMessage):
        pass

    def preprocess(self, msg_object: GuiMessage):

        if msg_object.get_cmd() == 'X':
            exit(0)
        elif msg_object.get_cmd() == 'L':
            self.qso_append_cli_input(msg_object)
            self.process_list_cmd(msg_object)
        elif msg_object.get_cmd() == 'E':
            self.qso_append_cli_input(msg_object)
            self.process_extended_cmd(msg_object)
        elif msg_object.get_cmd() == 'G':
            self.qso_append_cli_input(msg_object)
            self.process_get_cmd(msg_object)
        elif msg_object.get_cmd() == 'I':
            self.qso_append_cli_input(msg_object)
            self.process_info_cmd(msg_object)
        elif msg_object.get_cmd() == 'S':
            self.process_set_cmd(msg_object)
        elif msg_object.get_cmd() == 'C':
            self.qso_append_cli_input(msg_object)
            self.process_config_cmd(msg_object)
        elif msg_object.get_cmd() == 'P':
            self.qso_append_cli_input(msg_object)
            self.process_scan_cmd(msg_object)

    def process_mb_rsp(self, comms_msg: CommsMessage):
        processor = MbRspProcessors(comms_msg, self.b2f_q)
        # check to see if this is a listing, extended listing or post and process accordingly
        processor.parse_rx_message(comms_msg.get_payload())

        self.signal_reload('qso')

    def process_mb_notify(self, comms_msg: CommsMessage):
        # ToDo: we should only insert an entry in qso if we don't have an entry already
        processor = MbRspProcessors(comms_msg, self.b2f_q)
        # check to see if this is a listing, extended listing or post and process accordingly
        processor.parse_rx_message(comms_msg.get_payload())

        self.signal_reload('latest')
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
            fe_msg = self.f2b_q.get(block=False)
            if fe_msg:
                logging.logmsg(3, f"be: {fe_msg}")
                self.preprocess(fe_msg)
                self.f2b_q.task_done()
        except queue.Empty:
            pass  # nothing on the queue - do nothing

        # check for messages from the comms driver
        try:
            comms_rx = self.comms_rx_q.get(block=True, timeout=0.1)  # if no msg waiting, this will throw an exception
            log_text = ""  # add code here
            logging.logmsg(3, f"backend: {comms_rx}")
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
    
            # check for js8call message
    
            # run optimizing algorithms, e.g. harvesting info heard and caching
        pass
