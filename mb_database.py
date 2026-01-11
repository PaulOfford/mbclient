import os
import time
import sqlite3
from datetime import datetime, timezone

from logging import logmsg
from db_table import get_db_file_spec


hdr_time = time.time()
set_frequency = 14078000
set_offset = 1800


def iso_string_to_epoch(iso_str: str):
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        dt = datetime.strptime(iso_str, "%Y-%m-%d %H:%M")

    dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


class MbDatabase:
    db_file = None
    
    def __init__(self):
        self.db_file = get_db_file_spec()
        logmsg(1, f"mb_database: Working with database {self.db_file}")

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

        logmsg(1, "mb_database: Creating the progress table")
        cursor.execute("""CREATE TABLE progress (
            qso_date integer,
            blog text,
            station text,
            frequency integer,
            offset integer,
            message text
        )""")

        logmsg(1, "mb_database: Creating the status table")
        cursor.execute("""CREATE TABLE settings (ts float, name text, val text, typ text)""")

        logmsg(1, "mb_database: Loading default settings")
        with db:
            cursor.execute(
                "INSERT INTO settings VALUES (:ts, :name, :val, :typ)",
                {'ts': time.time(), 'name': 'startup_width', 'val': '1080', 'typ': 'integer'}
            )
            cursor.execute(
                "INSERT INTO settings VALUES (:ts, :name, :val, :typ)",
                {'ts': time.time(), 'name': 'startup_height', 'val': '640', 'typ': 'integer'}
            )
            cursor.execute(
                "INSERT INTO settings VALUES (:ts, :name, :val, :typ)",
                {'ts': time.time(), 'name': 'font_size', 'val': '10', 'typ': 'integer'}
            )
            cursor.execute(
                "INSERT INTO settings VALUES (:ts, :name, :val, :typ)",
                {'ts': time.time(), 'name': 'max_blogs', 'val': '30', 'typ': 'integer'}
            )
            cursor.execute(
                "INSERT INTO settings VALUES (:ts, :name, :val, :typ)",
                {'ts': time.time(), 'name': 'max_posts', 'val': '50', 'typ': 'integer'}
            )
            cursor.execute(
                "INSERT INTO settings VALUES (:ts, :name, :val, :typ)",
                {'ts': time.time(), 'name': 'use_gmt', 'val': '1', 'typ': 'integer'}
            )
            cursor.execute(
                "INSERT INTO settings VALUES (:ts, :name, :val, :typ)",
                {'ts': time.time(), 'name': 'max_listing', 'val': '5', 'typ': 'integer'}
            )

        logmsg(1, "mb_database: Creating the status table")
        cursor.execute("""CREATE TABLE status (
            last_checked float,
            hdr_updated float,
            post_updated float,
            post_list_updated float,
            progress_updated float,
            blog_updated float,
            radio_frequency integer,
            user_frequency integer,
            offset integer,
            is_scanning integer,
            callsign text,
            selected_blog text,
            selected_station text,
            selected_post integer
        )""")

        logmsg(1, "mb_database: Loading default status values")
        with db:
            cursor.execute(
                "INSERT INTO status VALUES ("
                ":last_checked, :hdr_updated, :post_updated, :post_list_updated, :blog_updated, :progress_updated, "
                ":radio_frequency, :user_frequency, :offset, :is_scanning, "
                ":callsign, :selected_blog, :selected_station, :selected_post"
                ")",
                {
                    'last_checked': 0,
                    'hdr_updated': 0,
                    'post_updated': 0,
                    'post_list_updated': 0,
                    'blog_updated': 0,
                    'progress_updated': 0,
                    'radio_frequency': 14078000,
                    'user_frequency': 14078000,
                    'offset': 1800,
                    'is_scanning': 0,
                    'callsign': "Pending",
                    'selected_blog': "M0PXO",
                    'selected_station': "",
                    'selected_post': 1
                }
            )

        logmsg(1, "mb_database: Creating post table")
        cursor.execute("""CREATE TABLE post (
            qso_date integer,
            blog text,
            station text,
            directed_to text,
            frequency integer,
            offset integer,
            cmd text,
            post_id integer,
            post_date integer,
            title text,
            body text,
            is_selected integer
        )""")

        logmsg(1, "mb_database: Creating blog table")
        cursor.execute("""CREATE TABLE blog (
            blog text,
            station text,
            frequency integer,
            snr integer,
            latest_post_id integer,
            latest_post_date integer,
            last_seen_date integer,
            info text,
            is_selected integer
        )""")

        blog_list = [
            {'blog': "M0PXO", 'station': "M0PXO", 'frequency': 14078000, 'snr': 1,
             'latest_post_id': "1", 'latest_post_date': "2026-01-05 17:10:00",
             'last_seen_date': "2026-01-05 17:15:00", 'info': "Sample server", 'is_selected': 1},
        ]

        logmsg(1, "mb_database: Loading list of demo blogs")
        for i, b in enumerate(blog_list):
            with db:
                cursor.execute(
                    "INSERT INTO blog VALUES (:blog, :station, :frequency, :snr,"
                    ":latest_post_id, :latest_post_date, :last_seen_date, :info, :is_selected)",
                    {
                        'blog': b['blog'],
                        'station': b['station'],
                        'frequency': b['frequency'],
                        'snr': b['snr'],
                        'latest_post_id': b['latest_post_id'],
                        'latest_post_date': iso_string_to_epoch(b['latest_post_date']),
                        'last_seen_date': iso_string_to_epoch(b['last_seen_date']),
                        'info': b['info'],
                        'is_selected': b['is_selected'],
                    }
                )

        welcome = [
            {
                'qso_date': '2026-01-05 17:11:00',
                'blog': 'M0PXO',
                'station': 'M0PXO',
                'directed_to': 'M7PJO',
                'frequency': 14078000,
                'offset': 1500,
                'cmd': '',
                'post_id': 1,
                'post_date': '2026-01-05 17:10:00',
                'title': 'Welcome to Microblogging',
                'body': 'Microblogging is a way to share short pieces of information via JS8 over HF or VHF.',
                'is_selected': 1
            },
        ]

        logmsg(1, "mb_database: Loading welcome info into the post table")
        for i, q in enumerate(welcome):
            with db:
                cursor.execute(
                    "INSERT INTO post VALUES (:qso_date, :blog, :station, :directed_to,"
                    " :frequency, :offset, :cmd, :post_id, :post_date, :title, :body, :is_selected)",
                    {
                        'qso_date': iso_string_to_epoch(q['qso_date']),
                        'blog': q['blog'],
                        'station': q['station'],
                        'directed_to': q['directed_to'],
                        'frequency': q['frequency'],
                        'offset': q['offset'],
                        'cmd': q['cmd'],
                        'post_id': q['post_id'],
                        'post_date': iso_string_to_epoch(q['post_date']),
                        'title': q['title'],
                        'body': q['body'],
                        'is_selected': q['is_selected']
                    }
                )

        logmsg(1, "mb_database: Closing the database connection")
        db.close()

    def migrate_from_v1(self):
        db = sqlite3.connect(self.db_file)
        cursor = db.cursor()

        # we need to merge the body from the 'post' type into 'listing' rows
        with db:
            # we need to set one of the posts as selected
            sql_cmd = "SELECT blog, post_id, body FROM qso WHERE type='post'"
            logmsg(1, f"mb_database: {sql_cmd}")
            cursor.execute(sql_cmd)
            rows = cursor.fetchall()

            for row in rows:
                body = row[2].replace("'", "''")
                sql_cmd = f"UPDATE qso SET body = '{body}' WHERE blog='{row[0]}' AND post_id={row[1]}"
                logmsg(1, f"mb_database: {sql_cmd}")
                cursor.execute(sql_cmd)

        # execute the SQL commands in db_migrate.sql
        f = open("./db_migrate.sql", "r")
        for sql_cmd in f.readlines():
            logmsg(1, f"mb_database: {sql_cmd[0:-2]}")
            with db:
                cursor.execute(sql_cmd)

        with db:
            # we need to set one of the posts as selected
            sql_cmd = "SELECT post_id FROM post ORDER BY post_id DESC LIMIT 1"
            logmsg(1, f"mb_database: {sql_cmd}")
            cursor.execute(sql_cmd)
            last_post = cursor.fetchone()

            sql_cmd = f"UPDATE status SET selected_post={last_post[0]}"
            logmsg(1, f"mb_database: {sql_cmd}")
            cursor.execute(sql_cmd)

            sql_cmd = f"UPDATE post SET is_selected=1 WHERE post_id={last_post[0]}"
            logmsg(1, f"mb_database: {sql_cmd}")
            cursor.execute(sql_cmd)

            sql_cmd = f"UPDATE status SET progress_updated = 0"
            logmsg(1, f"mb_database: {sql_cmd}")
            cursor.execute(sql_cmd)

        return
