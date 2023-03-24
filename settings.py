import time
import tkinter as tk
from db_table import *


class Settings:
    settings_cols = ['ts', 'name', 'val', 'typ']
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

    def get_setting(self, settings_table, name):
        db_values = settings_table.select(
            where=f"name='{name}'", order_by=None, desc=False, limit=1, hdr_list=self.settings_cols
        )
        value_str = db_values[0]['val']
        data_type = db_values[0]['typ']
        if data_type == 'integer':
            return int(value_str)
        elif data_type == 'float':
            return float(value_str)
        elif data_type == 'text':
            return value_str

    def set_setting(self, name: str, value: [int, float, str]):
        settings_table = DbTable('settings')
        settings_table.update(
            value_dictionary={'ts': time.time(), 'value': str(value)},
            where=f"name='{name}'"
        )

    def reload_settings(self):
        settings_table = DbTable('settings')
        self.startup_width = self.get_setting(settings_table, 'startup_width')
        self.startup_height = self.get_setting(settings_table, 'startup_height')
        self.startup_dimensions = f"{self.startup_width}x{self.startup_height}"
        self.font_size = self.get_setting(settings_table, 'font_size')
        self.max_latest = self.get_setting(settings_table, 'max_latest')
        self.max_qsos = self.get_setting(settings_table, 'max_qsos')
        self.max_blogs = self.get_setting(settings_table, 'max_blogs')
        self.max_listing = self.get_setting(settings_table, 'max_listing')

    def set_startup_width(self, width: int):
        self.set_setting('startup_width', width)

    def set_startup_height(self, height: int):
        self.set_setting('startup_height', height)

    def set_font_size(self, font_size: int):
        self.set_setting('font_size', font_size)

    def set_max_latest(self, max: int):
        self.set_setting('max_latest', max)

    def set_max_qsos(self, max: int):
        self.set_setting('max_qsos', max)

    def set_max_blogs(self, max: int):
        self.set_setting('max_blogs', max)

    def set_max_listing(self, max: int):
        self.set_setting('max_listing', max)


# ToDo: pivot this table to contain one row per setting; each row a key/value pair
settings = Settings()
