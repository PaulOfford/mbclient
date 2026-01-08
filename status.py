import time
from db_table import DbTable


class Status:
    status_cols = [
        'last_checked', 'hdr_updated', 'post_updated', 'post_list_updated', 'progress_updated', 'blog_updated',
        'radio_frequency', 'user_frequency', 'offset', 'is_scanning', 'callsign',
        'selected_blog', 'selected_station', 'selected_post'
    ]

    last_checked = 0  # timestamp of the last time we checked for updates
    hdr_updated = 0
    blog_updated = 0
    post_list_updated = 0
    post_updated = 0
    progress_updated = 0
    radio_frequency = 0
    user_frequency = 0
    offset = 0
    is_scanning = False
    req_outstanding = False
    callsign = ""
    selected_blog = ""
    selected_station = ""
    selected_post = 0

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
        self.post_updated = db_values['post_updated']
        self.post_list_updated = db_values['post_list_updated']
        self.progress_updated = db_values['progress_updated']
        self.blog_updated = db_values['blog_updated']
        self.radio_frequency = db_values['radio_frequency']
        self.user_frequency = db_values['user_frequency']
        self.is_scanning = db_values['is_scanning']
        self.callsign = db_values['callsign']
        self.selected_blog = db_values['selected_blog']
        self.selected_station = db_values['selected_station']
        self.selected_post = db_values['selected_post']

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

    def set_blog_updated(self):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'blog_updated': time.time()})
        self.reload_status()

    def set_post_list_updated(self):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'post_list_updated': time.time()})
        self.reload_status()

    def set_post_updated(self):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'post_updated': time.time()})
        self.reload_status()

    def set_progress_updated(self):
        status_table = DbTable('status')
        status_table.update(value_dictionary={'progress_updated': time.time()})
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
        self.set_blog_updated()

    def set_current_post(self, post: int):
        status_table = DbTable('status')
        status_table.update(
            value_dictionary={
                'selected_post': post
            }
        )
        self.set_post_updated()
