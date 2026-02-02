import os
import time
import sqlite3
import logging
from datetime import datetime, timezone
from mbclient.db_table import get_db_file_spec
logger = logging.getLogger(__name__)
hdr_time = time.time()
set_frequency = 14078000
set_offset = 1800

def iso_string_to_epoch(iso_str: str):
    try:
        dt = datetime.strptime(iso_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        dt = datetime.strptime(iso_str, '%Y-%m-%d %H:%M')
    dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()

class MbDatabase:
    db_file = None

    def __init__(self):
        self.db_file = get_db_file_spec()
        logger.info(f'mb_database: Working with database {self.db_file}')

    def determine_version(self):
        v1_columns = [('blogs',), ('qso',), ('settings',), ('status',)]
        v2_columns = [('blog',), ('post',), ('progress',), ('settings',), ('status',)]
        if os.path.exists(self.db_file):
            db = sqlite3.connect(self.db_file)
            cursor = db.cursor()
            with db:
                sql_cmd = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                cursor.execute(sql_cmd)
                rows = cursor.fetchall()
            if rows == v1_columns:
                version = 1
            elif rows == v2_columns:
                version = 2
            else:
                version = -1
        else:
            version = 0
        return version

    def create(self):
        if os.path.exists(self.db_file):
            os.remove(self.db_file)
        db = sqlite3.connect(self.db_file)
        cursor = db.cursor()
        logger.info('mb_database: Creating the progress table')
        cursor.execute('CREATE TABLE progress (\n            qso_date integer,\n            blog text,\n            station text,\n            frequency integer,\n            offset integer,\n            message text\n        )')
        logger.info('mb_database: Creating the status table')
        cursor.execute('CREATE TABLE settings (ts float, name text, val text, typ text)')
        logger.info('mb_database: Loading default settings')
        with db:
            cursor.execute('INSERT INTO settings VALUES (:ts, :name, :val, :typ)', {'ts': time.time(), 'name': 'startup_width', 'val': '1080', 'typ': 'integer'})
            cursor.execute('INSERT INTO settings VALUES (:ts, :name, :val, :typ)', {'ts': time.time(), 'name': 'startup_height', 'val': '640', 'typ': 'integer'})
            cursor.execute('INSERT INTO settings VALUES (:ts, :name, :val, :typ)', {'ts': time.time(), 'name': 'font_size', 'val': '10', 'typ': 'integer'})
            cursor.execute('INSERT INTO settings VALUES (:ts, :name, :val, :typ)', {'ts': time.time(), 'name': 'max_blogs', 'val': '30', 'typ': 'integer'})
            cursor.execute('INSERT INTO settings VALUES (:ts, :name, :val, :typ)', {'ts': time.time(), 'name': 'max_posts', 'val': '50', 'typ': 'integer'})
            cursor.execute('INSERT INTO settings VALUES (:ts, :name, :val, :typ)', {'ts': time.time(), 'name': 'use_gmt', 'val': '1', 'typ': 'integer'})
            cursor.execute('INSERT INTO settings VALUES (:ts, :name, :val, :typ)', {'ts': time.time(), 'name': 'max_listing', 'val': '5', 'typ': 'integer'})
        logger.info('mb_database: Creating the status table')
        cursor.execute('CREATE TABLE status (\n            last_checked float,\n            hdr_updated float,\n            post_updated float,\n            post_list_updated float,\n            progress_updated float,\n            blog_updated float,\n            radio_frequency integer,\n            user_frequency integer,\n            offset integer,\n            is_scanning integer,\n            callsign text,\n            selected_blog text,\n            selected_station text,\n            selected_post integer\n        )')
        logger.info('mb_database: Loading default status values')
        with db:
            cursor.execute('INSERT INTO status VALUES (:last_checked, :hdr_updated, :post_updated, :post_list_updated, :blog_updated, :progress_updated, :radio_frequency, :user_frequency, :offset, :is_scanning, :callsign, :selected_blog, :selected_station, :selected_post)', {'last_checked': 0, 'hdr_updated': 0, 'post_updated': 0, 'post_list_updated': 0, 'blog_updated': 0, 'progress_updated': 0, 'radio_frequency': 14078000, 'user_frequency': 14078000, 'offset': 1800, 'is_scanning': 0, 'callsign': 'Pending', 'selected_blog': 'M0PXO', 'selected_station': '', 'selected_post': 1})
        logger.info('mb_database: Creating post table')
        cursor.execute('CREATE TABLE post (\n            qso_date integer,\n            blog text,\n            station text,\n            directed_to text,\n            frequency integer,\n            offset integer,\n            cmd text,\n            post_id integer,\n            post_date integer,\n            title text,\n            body text,\n            is_selected integer\n        )')
        logger.info('mb_database: Creating blog table')
        cursor.execute('CREATE TABLE blog (\n            blog text,\n            station text,\n            frequency integer,\n            snr integer,\n            latest_post_id integer,\n            latest_post_date integer,\n            last_seen_date integer,\n            info text,\n            is_selected integer\n        )')
        blog_list = [{'blog': 'M0PXO', 'station': 'M0PXO', 'frequency': 14078000, 'snr': 1, 'latest_post_id': '1', 'latest_post_date': '2026-01-05 17:10:00', 'last_seen_date': '2026-01-05 17:15:00', 'info': 'Sample server', 'is_selected': 1}]
        logger.info('mb_database: Loading list of demo blogs')
        for i, b in enumerate(blog_list):
            with db:
                cursor.execute('INSERT INTO blog VALUES (:blog, :station, :frequency, :snr,:latest_post_id, :latest_post_date, :last_seen_date, :info, :is_selected)', {'blog': b['blog'], 'station': b['station'], 'frequency': b['frequency'], 'snr': b['snr'], 'latest_post_id': b['latest_post_id'], 'latest_post_date': iso_string_to_epoch(b['latest_post_date']), 'last_seen_date': iso_string_to_epoch(b['last_seen_date']), 'info': b['info'], 'is_selected': b['is_selected']})
        welcome = [{'qso_date': '2026-01-05 17:11:00', 'blog': 'M0PXO', 'station': 'M0PXO', 'directed_to': 'M7PJO', 'frequency': 14078000, 'offset': 1500, 'cmd': '', 'post_id': 1, 'post_date': '2026-01-05 17:10:00', 'title': 'Welcome to Microblogging', 'body': 'Microblogging is a way to share short pieces of information via JS8 over HF or VHF.', 'is_selected': 1}]
        logger.info('mb_database: Loading welcome info into the post table')
        for i, q in enumerate(welcome):
            with db:
                cursor.execute('INSERT INTO post VALUES (:qso_date, :blog, :station, :directed_to, :frequency, :offset, :cmd, :post_id, :post_date, :title, :body, :is_selected)', {'qso_date': iso_string_to_epoch(q['qso_date']), 'blog': q['blog'], 'station': q['station'], 'directed_to': q['directed_to'], 'frequency': q['frequency'], 'offset': q['offset'], 'cmd': q['cmd'], 'post_id': q['post_id'], 'post_date': iso_string_to_epoch(q['post_date']), 'title': q['title'], 'body': q['body'], 'is_selected': q['is_selected']})
        logger.info('mb_database: Closing the database connection')
        db.close()

    def migrate_from_v1(self):
        db = sqlite3.connect(self.db_file)
        cursor = db.cursor()
        with db:
            sql_cmd = "SELECT blog, post_id, body FROM qso WHERE type='post'"
            logger.info(f'mb_database: {sql_cmd}')
            cursor.execute(sql_cmd)
            rows = cursor.fetchall()
            for row in rows:
                body = row[2].replace("'", "''")
                sql_cmd = f"UPDATE qso SET body = '{body}' WHERE blog='{row[0]}' AND post_id={row[1]}"
                logger.info(f'mb_database: {sql_cmd}')
                cursor.execute(sql_cmd)
        f = open('./db_migrate.sql', 'r')
        for sql_cmd in f.readlines():
            logger.info(f'mb_database: {sql_cmd[0:-2]}')
            with db:
                cursor.execute(sql_cmd)
        with db:
            sql_cmd = 'SELECT post_id FROM post ORDER BY post_id DESC LIMIT 1'
            logger.info(f'mb_database: {sql_cmd}')
            cursor.execute(sql_cmd)
            last_post = cursor.fetchone()
            sql_cmd = f'UPDATE status SET selected_post={last_post[0]}'
            logger.info(f'mb_database: {sql_cmd}')
            cursor.execute(sql_cmd)
            sql_cmd = f'UPDATE post SET is_selected=1 WHERE post_id={last_post[0]}'
            logger.info(f'mb_database: {sql_cmd}')
            cursor.execute(sql_cmd)
            sql_cmd = f'UPDATE status SET progress_updated = 0'
            logger.info(f'mb_database: {sql_cmd}')
            cursor.execute(sql_cmd)
        return