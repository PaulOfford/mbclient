import time
from db_table import *


class Status:
    settings_cols = [
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

    def __init__(self):
        self.reload_status()

    def reload_status(self):
        status_table = DbTable('status')
        db_values = status_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=self.settings_cols
        )
        self.hdr_updated = db_values[0]['hdr_updated']
        self.latest_updated = db_values[0]['latest_updated']
        self.qso_updated = db_values[0]['qso_updated']
        self.blogs_updated = db_values[0]['blogs_updated']
        self.radio_frequency = db_values[0]['radio_frequency']
        self.user_frequency = db_values[0]['user_frequency']
        self.callsign = db_values[0]['callsign']

        if db_values[0]['is_scanning']:
            self.is_scanning = True
        else:
            self.is_scanning = False

        if db_values[0]['req_outstanding']:
            self.req_outstanding = True
        else:
            self.req_outstanding = False

    def update_last_checked(self):
        self.last_checked = time.time()
