from db_table import *


class Settings:
    settings_cols = ['startup_width', 'startup_height', 'font_size', 'max_latest', 'max_qsos', 'max_blogs']
    startup_width = None
    startup_height = None
    startup_dimensions = None
    font_size = None
    max_latest = None
    max_qsos = None
    max_blogs = None
    max_listing = 5  # ToDo: put this in the database

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


# ToDo: pivot this table to contain one row per setting; each row a key/value pair
settings = Settings()
