import time
from mbclient.db_table import *

class Settings:
    db_file = None
    settings_cols = ['ts', 'name', 'val', 'typ']
    startup_width = None
    startup_height = None
    startup_dimensions = None
    font_size = None
    max_posts = None
    max_blogs = None
    max_listing = 5
    use_gmt = 1
    settings_table = None

    def __init__(self):
        self.settings_table = DbTable('settings')
        self.reload_settings()

    def get_setting(self, name):
        db_values = self.settings_table.select(where=f"name='{name}'", order_by=None, desc=False, limit=1, hdr_list=self.settings_cols)
        if len(db_values) > 0:
            value_str = db_values[0]['val']
            data_type = db_values[0]['typ']
            if data_type == 'integer':
                return int(value_str)
            elif data_type == 'float':
                return float(value_str)
            elif data_type == 'text':
                return value_str
        else:
            return 'unknown'

    def set_setting(self, name: str, value):
        self.settings_table.update(value_dictionary={'ts': time.time(), 'val': str(value)}, where=f"name='{name}'")

    def reload_settings(self):
        self.startup_width = self.get_setting('startup_width')
        self.startup_height = self.get_setting('startup_height')
        self.startup_dimensions = f'{self.startup_width}x{self.startup_height}'
        self.font_size = self.get_setting('font_size')
        self.max_posts = self.get_setting('max_posts')
        self.max_blogs = self.get_setting('max_blogs')
        self.max_listing = self.get_setting('max_listing')
        self.use_gmt = self.get_setting('use_gmt')

    def set_startup_width(self, width: int):
        self.set_setting('startup_width', width)

    def set_startup_height(self, height: int):
        self.set_setting('startup_height', height)

    def set_font_size(self, font_size: int):
        self.set_setting('font_size', font_size)

    def set_max_blogs(self, limit: int):
        self.set_setting('max_blogs', limit)

    def set_max_posts(self, limit: int):
        self.set_setting('max_posts', limit)

    def set_use_gmt(self, choice: bool):
        if choice:
            self.set_setting('use_gmt', 1)
        else:
            self.set_setting('use_gmt', 0)