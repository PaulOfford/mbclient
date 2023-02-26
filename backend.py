from settings import *
from message_q import *
from logging import *
from time import sleep


class BeProcessor:

    qso_fields = [
        {'db_col': 'qso_date'},
        {'db_col': 'type'},
        {'db_col': 'blog'},
        {'db_col': 'station'},
        {'db_col': 'directed_to'},
        {'db_col': 'frequency'},
        {'db_col': 'offset'},
        {'db_col': 'cmd'},
        {'db_col': 'rsp'},
        {'db_col': 'post_id'},
        {'db_col': 'post_date'},
        {'db_col': 'title'},
        {'db_col': 'body'},
    ]

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

    def qso_append_cli_input(self, cli_input: str, rsp_text: str):
        self.status.reload_status()
        qso_table = DbTable('qso')
        db_values = qso_table.select(limit=1, hdr_list=self.qso_fields)
        for row in db_values:
            row['qso_date'] = time.time()
            row['type'] = 'cmd'
            row['blog'] = self.status.selected_blog
            row['station'] = self.status.selected_station
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
        notify = B2fMessage(self.b2f_q)
        notify.signal_reload('qso')

    def qso_append_progress(self, cli_input: str, rsp_text: str):
        self.status.reload_status()
        qso_table = DbTable('qso')
        db_values = qso_table.select(limit=1, hdr_list=self.qso_fields)
        for row in db_values:
            row['qso_date'] = time.time()
            row['type'] = 'progress'
            row['blog'] = self.status.selected_blog
            row['station'] = self.status.selected_station
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
        notify = B2fMessage(self.b2f_q)
        notify.signal_reload('qso')

    # when we call this function, the post_id_list must contain post_ids in numerical order
    def get_posts_via_cache(self, req: dict, post_id_list: list):

        blog = req['blog']
        station = req['station']
        cmd = req['cmd']

        svr_request_list = []  # this is a list of post_ids we will need to request from the server

        # set up the list of dictionaries fo the results
        init_vals = {'post_id': 0, 'has_entry': False, 'date': 0, 'title': '', 'body': ''}

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
                        {'has_entry': True, 'date': row['post_date'], 'title': row['title'], 'body': row['body']}
                    )
                    row['qso_date'] = time.time()
                    row['directed_to'] = self.status.callsign
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
        self.qso_append_progress('Requesting details from the server for: ', f"{svr_request_list}")

        payload = f"{cmd}{posts_needed}~"
        logmsg(3, 'comms: send: ' + str(payload))
        mblog_api_req = CommsMsg(self.comms_tx_q)

        mblog_api_req.set_ts(time.time())
        mblog_api_req.set_direction('tx')
        mblog_api_req.set_source(self.status.callsign)
        mblog_api_req.set_destination(self.status.selected_station)
        mblog_api_req.set_snr(0)
        mblog_api_req.set_typ('mb_req')
        mblog_api_req.set_target('mb_service')
        mblog_api_req.set_obj('service')
        mblog_api_req.set_payload(str(payload))
        self.comms_tx_q.put(mblog_api_req)

        return return_values

    @staticmethod
    def get_posts_tail(blog: str, station: str):
        fields = [
            {'db_col': 'latest_post_id'},
            {'db_col': 'latest_post_date'},
        ]

        blogs_table = DbTable('blogs')
        db_values = blogs_table.select(order_by='latest_post_id', desc=True, limit=1,
                                       where=f"blog='{blog}' and station='{station}'", hdr_list=fields)
        return db_values

    def process_list_cmd(self, req: dict):
        # If the request is to list based on a date or dates, we need to go to the server
        # because we have no way of knowing if we have all posts with a certain date.
        # If the request is a TAIL listing, we need to get the latest post number from the
        # blogs table as the range end, subtract from it the max_listing value to get a range start
        # and then get everything in that range.
        # If the request is to list a specific post by post id, simply check the cache for that.

        post_ids = []

        if req['op'] == 'eq':
            post_ids.append(req['post_id'])
        elif req['op'] == 'gt':
            for i in range(settings.max_listing):
                post_ids.append(req['post_id'] + 1 + i)
        elif req['op'] == 'tail':
            # get the latest post id for this blog
            latest_post = self.get_posts_tail(req['blog'], req['station'])

            for i in range(
                    latest_post[0]['latest_post_id'] - settings.max_listing + 1,
                    latest_post[0]['latest_post_id'] + 1
            ):
                post_ids.append(i)

        # do we have any of the information in the cache
        self.get_posts_via_cache(req, post_ids)

        # get the frontend to reload the qso box
        notify = B2fMessage(self.b2f_q)
        notify.signal_reload('qso')
        return

    def process_extended_cmd(self, req: dict):
        self.process_list_cmd(req)

    def process_get_cmd(self, req: dict):
        post_ids = [req['post_id']]
        self.get_posts_via_cache(req, post_ids)
        notify = B2fMessage(self.b2f_q)
        notify.signal_reload('qso')
        return

    def process_info_cmd(self, req: dict):
        pass

    def process_set_cmd(self, req: dict):
        blog = req['blog']
        station = req['station']
        if len(blog) > 0:
            if len(station) > 0:
                s = DbTable('status')
                s.update(where=None, value_dictionary={'selected_blog': blog})
                s.update(where=None, value_dictionary={'selected_station': station})

                # update the selected row
                b = DbTable('blogs')
                b.update(where=None, value_dictionary={'is_selected': 0})
                b.update(where=f"blog='{blog}' AND station='{station}'", value_dictionary={'is_selected': 1})

                s.update(where=None, value_dictionary={'cli_updated': time.time()})
                s.update(where=None, value_dictionary={'blogs_updated': time.time()})

                # send OK back to the frontend
                rsp = B2fMessage(self.b2f_q)
                rsp.clone_req_msg(req)
                rsp.msg['rc'] = 0
                self.b2f_q.put(rsp.msg)

    def process_config_cmd(self, msg: dict):
        pass

    def process_scan_cmd(self, msg: dict):
        pass

    def preprocess(self, msg: dict):

        self.qso_append_cli_input(msg['cli_input'], '')

        if msg['cmd'] == 'L':
            self.process_list_cmd(msg)
        elif msg['cmd'] == 'E':
            self.process_extended_cmd(msg)
        elif msg['cmd'] == 'G':
            self.process_get_cmd(msg)
        elif msg['cmd'] == 'I':
            self.process_info_cmd(msg)
        elif msg['cmd'] == 'S':
            self.process_set_cmd(msg)
        elif msg['cmd'] == 'C':
            self.process_config_cmd(msg)
        elif msg['cmd'] == 'P':
            self.process_scan_cmd(msg)
        elif msg['cmd'] == 'X':
            exit(0)

    def process_mb_rsp(self, comms_msg: dict):
        pass

    def process_mb_notify(self, comms_msg: dict):
        pass

    def process_status_radio_frequency(self, comms_msg: dict):
        pass

    def process_status_offset(self, comms_msg: dict):
        pass

    def process_status_callsign(self, comms_msg: dict):
        pass

    def process_comms_rx(self, comms_msg: dict):
        if comms_msg.get('typ') == 'mb_rsp':
            self.process_mb_rsp(comms_msg)
        elif comms_msg.get('typ') == 'mb_notify':
            self.process_mb_notify(comms_msg)
        elif comms_msg.get('typ') == 'control' and comms_msg.get('target') == 'status'\
                and comms_msg.get('obj') == 'radio_frequency':
            self.process_status_radio_frequency(comms_msg)
        elif comms_msg.get('typ') == 'control' and comms_msg.get('target') == 'status'\
                and comms_msg.get('obj') == 'offset':
            self.process_status_offset(comms_msg)
        elif comms_msg.get('typ') == 'control' and comms_msg.get('target') == 'status'\
                and comms_msg.get('obj') == 'callsign':
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
            comms_rx = self.comms_rx_q.get(block=False)  # if no msg waiting, this will throw an exception
            logging.logmsg(3, f"comms: {comms_rx}")
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
            sleep(0.5)  # we need this else the backend thread hogs the cpu
    
            # check for js8call message
    
            # run optimizing algorithms, e.g. harvesting info heard and caching
        pass
