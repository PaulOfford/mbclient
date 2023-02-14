from db_table import *


class Settings:
    settings_cols = [
        {'db_col': 'startup_width'},
        {'db_col': 'startup_height'},
        {'db_col': 'font_size'},
        {'db_col': 'max_latest'},
        {'db_col': 'max_qsos'},
        {'db_col': 'max_blogs'},
    ]
    startup_width = 640
    startup_height = 480
    startup_dimensions = f"{startup_width}x{startup_height}"
    font_size = 8
    max_latest = 1
    max_qsos = 1
    max_blogs = 1

    def __init__(self):
        self.reload_settings()

    def reload_settings(self):
        settings_table = DbTable('settings')
        db_values = settings_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=self.settings_cols
        )
        self.startup_width = db_values[0]['startup_width']
        self.startup_height = db_values[0]['startup_height']
        self.startup_dimensions = f"{self.startup_width}x{self.startup_height}"
        self.font_size = db_values[0]['font_size']
        self.max_latest = db_values[0]['max_latest']
        self.max_qsos = db_values[0]['max_qsos']
        self.max_blogs = db_values[0]['max_blogs']

settings = Settings()
