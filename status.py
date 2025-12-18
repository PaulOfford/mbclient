import time
from db_table import *


class Status:
    status_cols = ['last_checked', 'hdr_updated', 'latest_updated', 'qso_updated', 'cli_updated', 'blogs_updated',
                   'radio_frequency', 'user_frequency', 'offset', 'is_scanning', 'req_outstanding', 'callsign',
                   'selected_blog', 'selected_station']

    last_checked = 0  # timestamp of the last time we checked for updates
    hdr_updated = 0
    latest_updated = 0
    qso_updated = 0
    blogs_updated = 0
    cli_updated = 0
    radio_frequency = 0
    user_frequency = 0
    offset = 0
    is_scanning = False
    req_outstanding = False
    callsign = ""
    selected_blog = ""
    selected_station = ""

    def __init__(self):
        self.reload_status()

    def reload_status(self):
        status_table = DbTable('status')
        db_values_list = status_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=self.status_cols
        )
        db_values = db_values_list[0]
        self.last_checked = db_values['last_checked']
        self.hdr_updated = db_values['hdr_updated']
        self.latest_updated = db_values['latest_updated']
        self.qso_updated = db_values['qso_updated']
        self.cli_updated = db_values['cli_updated']
        self.blogs_updated = db_values['blogs_updated']
        self.radio_frequency = db_values['radio_frequency']
        self.user_frequency = db_values['user_frequency']
        self.is_scanning = db_values['is_scanning']
        self.req_outstanding = db_values['req_outstanding']
        self.callsign = db_values['callsign']
        self.selected_blog = db_values['selected_blog']
        self.selected_station = db_values['selected_station']

    def update_last_checked(self):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'last_checked': time.time()})
        self.reload_status()

    def set_selected_blog(self, blog: str, station: str):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'selected_blog': blog})
        status_table.update(value_dictionary={'selected_station': station})
        self.reload_status()

    def set_hdr_updated(self):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'hdr_updated': time.time()})
        self.reload_status()

    def set_latest_updated(self):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'latest_updated': time.time()})
        self.reload_status()

    def set_qso_updated(self):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'qso_updated': time.time()})
        self.reload_status()

    def set_cli_updated(self):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'cli_updated': time.time()})
        self.reload_status()

    def set_blogs_updated(self):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'blogs_updated': time.time()})
        self.reload_status()

    def set_current_blog(self, blog: str, station: str, frequency: int):
        status_table = DbTable('status')
        status_table.update(
            value_dictionary={
                'selected_blog': blog,
                'selected_station': station,
                'user_frequency': frequency,
                'radio_frequency': frequency
            }
        )
        self.set_blogs_updated()
