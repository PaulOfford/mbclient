import sqlite3
from settings import *
import os
import time

if os.path.exists(db_file):
  os.remove(db_file)

db = sqlite3.connect(db_file)

c = db.cursor()

# status table - the columns starting with the frme name and ending _updated
# hold the epoch time that data associated with that frame.
# the is_scanning and req_outstanding integers are used as booleans, o - False and 1 - True.
#
c.execute("""CREATE TABLE status (
    hdr_updated integer,
    latest_updated integer,
    qso_updated integer,
    blogs_updated integer,
    radio_frequency real,
    user_frequency real,
    is_scanning integer,
    req_outstanding integer,
    selected_blog_id integer
)""")

c.execute("""CREATE TABLE latest (
    blog_name text,
    station_name text,
    frequency real,
    post_id integer,
    post_date integer,
    title text
)""")

c.execute("""CREATE TABLE qso (
    blog_name text,
    station_name text,
    frequency real,
    post_id integer,
    post_date integer,
    title text,
    body text
)""")

c.execute("""CREATE TABLE blogs (
    blog_name text,
    station_name text,
    frequency integer,
    snr integer,
    capabilities text,
    latest_post_id integer,
    latest_post_date integer,
    last_seen_date integer,
    is_selected integer
)""")

blog_list = [
    {'blog_name':"AUSNEWS", 'station_name':"VK3WXY", 'frequency':14078000, 'snr':-25, 'capabilities':"LEGU", 'latest_post_date':"2023-02-07 23:10", 'latest_post_id':"405", 'last_seen_date':"2023-02-09 18:02", 'is_selected':0},
    {'blog_name':"M0PXO", 'station_name':"M0PXO", 'frequency':14078000, 'snr':1, 'capabilities':"LEG", 'latest_post_date':"2023-02-03 10:06", 'latest_post_id':"29", 'last_seen_date':"2023-02-10 10:23", 'is_selected':1},
    {'blog_name':"NEWSEN", 'station_name':"K7GHI", 'frequency':14078000, 'snr':-24, 'capabilities':"LEG", 'latest_post_date':"2023-01-31 11:23", 'latest_post_id':"36", 'last_seen_date':"2023-02-05 22:10", 'is_selected':0},
    {'blog_name':"NEWSEN", 'station_name':"K7MNO", 'frequency':14078000, 'snr':-13, 'capabilities':"LEG", 'latest_post_date':"2023-01-30 07:03", 'latest_post_id':"35", 'last_seen_date':"2023-02-06 07:45", 'is_selected':0},
    # {'blog_name':"NEWSSP", 'station_name':"K7MNO", 'frequency':14078000, 'snr':-14, 'capabilities':"LEG", 'latest_post_date':"2023-01-27 09:45", 'latest_post_id':"14", 'last_seen_date':"2023-02-06 07:18", 'is_selected':0},
    {'blog_name':"9Q1AB", 'station_name':"9Q1AB", 'frequency':14078000, 'snr':-16, 'capabilities':"LEG", 'latest_post_date':"2023-02-07 13:44", 'latest_post_id':"182", 'last_seen_date':"2023-02-10 10:25", 'is_selected':0},
]

for i, b in enumerate(blog_list):
    with db:
        c.execute("INSERT INTO blogs VALUES (:blog_name, :station_name, :frequency, :snr, :capabilities,"
                ":latest_post_id, :latest_post_date, :last_seen_date, :is_selected)",
                {
                    'blog_name': b['blog_name'],
                    'station_name': b['station_name'],
                    'frequency': b['frequency'],
                    'snr': b['snr'],
                    'capabilities': b['capabilities'],
                    'latest_post_id': b['latest_post_id'],
                    'latest_post_date': time.mktime(time.strptime(b['latest_post_date'], "%Y-%m-%d %H:%M")),
                    'last_seen_date': time.mktime(time.strptime(b['last_seen_date'], "%Y-%m-%d %H:%M")),
                    'is_selected': b['is_selected'],
                })


db.close()
