import time
from db_table import *


class Status:
    status_cols = [
        {'db_col': 'hdr_updated'},
        {'db_col': 'latest_updated'},
        {'db_col': 'qso_updated'},
        {'db_col': 'blogs_updated'},
        {'db_col': 'radio_frequency'},
        {'db_col': 'user_frequency'},
        {'db_col': 'offset'},
        {'db_col': 'is_scanning'},
        {'db_col': 'req_outstanding'},
        {'db_col': 'callsign'},
        {'db_col': 'selected_blog'},
    ]

    last_checked = 0  # timestamp of the last time we checked for updates

    hdr_updated = 0
    latest_updated = 0
    qso_updated = 0
    blogs_updated = 0
    radio_frequency = 0
    user_frequency = 0
    offset = 0
    is_scanning = False
    req_outstanding = False
    callsign = ""
    selected_blog = ""

    def __init__(self):
        self.reload_status()

    def reload_status(self):
        status_table = DbTable('status')
        db_values = status_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=self.status_cols
        )
        self.hdr_updated = db_values[0]['hdr_updated']
        self.latest_updated = db_values[0]['latest_updated']
        self.qso_updated = db_values[0]['qso_updated']
        self.blogs_updated = db_values[0]['blogs_updated']
        self.radio_frequency = db_values[0]['radio_frequency']
        self.user_frequency = db_values[0]['user_frequency']
        self.is_scanning = db_values[0]['is_scanning']
        self.req_outstanding = db_values[0]['req_outstanding']
        self.callsign = db_values[0]['callsign']
        self.selected_blog = db_values[0]['selected_blog']

    def update_last_checked(self):
        self.last_checked = time.time()

    def set_selected_blog(self, blog: str):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'selected_blog': blog})
        status.reload_status()


status = Status()
