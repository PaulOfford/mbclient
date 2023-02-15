from settings import *
import os
import time

load_samples = True

if os.path.exists(db_file):
    os.remove(db_file)

db = sqlite3.connect(db_file)

c = db.cursor()

# status table - the columns starting with the frame name and ending _updated
# hold the epoch time that data associated with that frame.
# the is_scanning and req_outstanding integers are used as booleans, o - False and 1 - True.
#
c.execute("""CREATE TABLE settings (
    startup_width integer,
    startup_height integer,
    font_size integer,
    max_latest integer,
    max_qsos integer,
    max_blogs integer
)""")

with db:
    c.execute("INSERT INTO settings VALUES (:startup_width, :startup_height, :font_size, "
              ":max_latest, :max_qsos, :max_blogs)",
              {
                  'startup_width': 1080,
                  'startup_height': 640,
                  'font_size': 8,
                  'max_latest': 30,
                  'max_qsos': 50,
                  'max_blogs': 30
              }
              )

c.execute("""CREATE TABLE status (
    hdr_updated integer,
    latest_updated integer,
    qso_updated integer,
    cli_updated integer,
    blogs_updated integer,
    radio_frequency integer,
    user_frequency integer,
    offset integer,
    is_scanning integer,
    req_outstanding integer,
    callsign text,
    selected_blog text
)""")

with db:
    c.execute(
        "INSERT INTO status VALUES ("
        ":hdr_updated, :latest_updated, :qso_updated, :blogs_updated, :cli_updated, "
        ":radio_frequency, :user_frequency, :offset, :is_scanning, :req_outstanding, "
        ":callsign, :selected_blog"
        ")",
        {
            'hdr_updated': 0,
            'latest_updated': 0,
            'qso_updated': 0,
            'cli_updated': 0,
            'blogs_updated': 0,
            'radio_frequency': 0,
            'user_frequency': 0,
            'offset': 0,
            'is_scanning': 0,
            'req_outstanding': 0,
            'callsign': "Pending",
            'selected_blog': ""
        }
    )

c.execute("""CREATE TABLE qso (
    qso_date integer,
    blog text,
    station text,
    directed_to text,
    frequency integer,
    offset integer,
    cmd text,
    rsp text,
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

if load_samples:

    blog_list = [
        {'blog_name': "AUSNEWS", 'station_name': "VK3WXY", 'frequency': 14078000, 'snr': -25,
         'capabilities': "LEGU", 'latest_post_date': "2023-02-07 23:10", 'latest_post_id': "405",
         'last_seen_date': "2023-02-09 18:02", 'is_selected': 0},
        {'blog_name': "M0PXO", 'station_name': "M0PXO", 'frequency': 14078000, 'snr': 1,
         'capabilities': "LEG", 'latest_post_date': "2023-02-03 10:06", 'latest_post_id': "29",
         'last_seen_date': "2023-02-10 10:23", 'is_selected': 1},
        {'blog_name': "NEWSEN", 'station_name': "K7GHI", 'frequency': 14078000, 'snr': -24,
         'capabilities': "LEG", 'latest_post_date': "2023-01-31 11:23", 'latest_post_id': "36",
         'last_seen_date': "2023-02-05 22:10", 'is_selected': 0},
        {'blog_name': "NEWSEN", 'station_name': "K7MNO", 'frequency': 14078000, 'snr': -13,
         'capabilities': "LEG", 'latest_post_date': "2023-01-30 07:03", 'latest_post_id': "35",
         'last_seen_date': "2023-02-06 07:45", 'is_selected': 0},
        # {'blog_name': "NEWSSP", 'station_name': "K7MNO", 'frequency': 14078000, 'snr': -14,
        # 'capabilities': "LEG", 'latest_post_date': "2023-01-27 09:45", 'latest_post_id': "14",
        # 'last_seen_date': "2023-02-06 07:18", 'is_selected': 0},
        {'blog_name': "9Q1AB", 'station_name': "9Q1AB", 'frequency': 14078000, 'snr': -16,
         'capabilities': "LEG", 'latest_post_date': "2023-02-07 13:44", 'latest_post_id': "182",
         'last_seen_date': "2023-02-10 10:25", 'is_selected': 0},
    ]

    for i, b in enumerate(blog_list):
        with db:
            c.execute(
                "INSERT INTO blogs VALUES (:blog_name, :station_name, :frequency, :snr, :capabilities,"
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
                }
            )

    hdr_time = time.time()
    set_frequency = 14078000
    set_offset = 1800
    set_callsign = "2E0FGO"

    with db:
        c.execute(
            f"UPDATE status SET "
            f"hdr_updated={hdr_time}, radio_frequency={set_frequency}, user_frequency={set_frequency}, "
            f"offset={set_offset}, callsign='{set_callsign}'")

    qsos = [
        {
            'qso_date': '2023-02-07 14:25:48',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.L >0',
            'rsp': 'OK',
            'post_id': 20,
            'post_date': '1970-01-01 00:00:00',
            'title': 'MARINES TO GAIN RADIO OP EXPERIENCE',
            'body': ''
        },
        {
            'qso_date': '2023-02-07 14:25:48',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.L >0',
            'rsp': 'OK',
            'post_id': 21,
            'post_date': '1970-01-01 00:00:00',
            'title': 'MORE HAMS ON THE ISS',
            'body': ''
        },
        {
            'qso_date': '2023-02-07 14:25:48',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.L >0',
            'rsp': 'OK',
            'post_id': 22,
            'post_date': '1970-01-01 00:00:00',
            'title': 'HAARP THANKS HAMS',
            'body': ''
        },
        {
            'qso_date': '2023-02-07 14:25:48',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.L >0',
            'rsp': 'OK',
            'post_id': 23,
            'post_date': '1970-01-01 00:00:00',
            'title': 'K7RA SOLAR UPDATE',
            'body': ''
        },
        {
            'qso_date': '2023-02-07 14:25:48',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.L >0',
            'rsp': 'OK',
            'post_id': 24,
            'post_date': '1970-01-01 00:00:00',
            'title': 'RSGB PROPOGATION NEWS',
            'body': ''
        },

        {
            'qso_date': '2023-02-07 18:07:28',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.L >0',
            'rsp': 'OK',
            'post_id': 20,
            'post_date': '2022-12-22 12:00:00',
            'title': 'MARINES TO GAIN RADIO OP EXPERIENCE',
            'body': ''
        },
        {
            'qso_date': '2023-02-07 18:07:28',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.L >0',
            'rsp': 'OK',
            'post_id': 21,
            'post_date': '2023-01-06 12:00:00',
            'title': 'MORE HAMS ON THE ISS',
            'body': ''
        },
        {
            'qso_date': '2023-02-07 18:07:28',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.L >0',
            'rsp': 'OK',
            'post_id': 22,
            'post_date': '2023-01-13 12:00:00',
            'title': 'HAARP THANKS HAMS',
            'body': ''
        },
        {
            'qso_date': '2023-02-07 18:07:28',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.L >0',
            'rsp': 'OK',
            'post_id': 23,
            'post_date': '2023-01-13 12:00:00',
            'title': 'K7RA SOLAR UPDATE',
            'body': ''
        },
        {
            'qso_date': '2023-02-07 18:07:28',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.L >0',
            'rsp': 'OK',
            'post_id': 24,
            'post_date': '2023-01-15 12:00:00',
            'title': 'RSGB PROPOGATION NEWS',
            'body': ''
        },
        {
            'qso_date': '2023-02-07 18:10:02',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.G 24',
            'rsp': 'OK',
            'post_id': 24,
            'post_date': '1970-01-01 00:00:00',
            'title': 'RSGB Propogation News',
            'body':
                "PROPAGATION NEWS - 15 JANUARY 2023\n\n"
                "SUNSPOT REGION 3186 HAS ROTATED INTO VIEW OFF THE SUN'S NORTHEAST LIMB AND PRODUCE"
                " AN X1.0 SOLAR FLARE AT 2247UTC ON THE 10 JANUARY. IT MAY HAVE THROWN SOME PLASMA INTO"
                " SPACE IN THE FORM OF A CORONAL MASS EJECTION BUT, AS IT IS NOT YET DIRECTLY FACING EARTH,"
                " THE CME IS LIKELY DIRECTED AWAY FROM US.\n\n"
                "WE CURRENTLY HAVE AN SFI IN THE 190S."
        },
        {
            'qso_date': '2023-02-07 14:28:47',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': '2E0FGO',
            'frequency': 14078000,
            'offset': 1800,
            'cmd': 'M.G 25',
            'rsp': 'OK',
            'post_id': 25,
            'post_date': '2023-01-20 12:00:00',
            'title': '',
            'body':
                "AMATEUR SATELLITE FALCONSAT-3 NEARS REENTRY\n\n"
                "2023-01-20\n"
                "FS-3 IS PREDICTED TO REENTER THE EARTHS ATMOSPHERE IN THE WEEK OF JANUARY 16 - 21, 2023."
                "  RADIO AMATEUR SATELLITE CORPORATION (AMSAT) BOARD MEMBER AND FS-3 CONTROL OPERATOR, MARK HAMMOND,"
                " N8MH, SAID HE WILL TRY TO HAVE THE SATELLITE OPERATIONAL FOR ITS FINAL HOURS.\n\n"
                "THE SATELLITE HAS ONLY BEEN AVAILABLE FOR APPROXIMATELY 24 HOURS EACH WEEKEND DUE TO WEAK BATTERIES.\n"
        },
    ]

    for i, q in enumerate(qsos):
        with db:
            c.execute(
                "INSERT INTO qso VALUES (:qso_date, :blog, :station, :directed_to,"
                " :frequency, :offset, :cmd, :rsp, :post_id, :post_date, :title, :body)",
                {
                    'qso_date': time.mktime(time.strptime(q['qso_date'], "%Y-%m-%d %H:%M:%S")),
                    'blog': q['blog'],
                    'station': q['station'],
                    'directed_to': q['directed_to'],
                    'frequency': q['frequency'],
                    'offset': q['offset'],
                    'cmd': q['cmd'],
                    'rsp': q['rsp'],
                    'post_id': q['post_id'],
                    'post_date': time.mktime(time.strptime(q['post_date'], "%Y-%m-%d %H:%M:%S")),
                    'title': q['title'],
                    'body': q['body'],
                }
            )

    latest = [
        {
            'qso_date': '2023-02-13 22:24:48',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': 'M7PJO',
            'frequency': 28078000,
            'offset': 1500,
            'cmd': '',
            'rsp': 'OK',
            'post_id': 40,
            'post_date': '1970-01-01 00:00:00',
            'title': 'TURKEY/SYRIA LATEST',
            'body': ''
        },
        {
            'qso_date': '2023-02-13 01:25:48',
            'blog': 'M0PXO',
            'station': 'M0PXO',
            'directed_to': 'M7PJO',
            'frequency': 28078000,
            'offset': 1500,
            'cmd': '',
            'rsp': 'OK',
            'post_id': 39,
            'post_date': '2023-02-13 01:15:22',
            'title': 'NZ BRACED FOR CYCLONE',
            'body': ''
        },
    ]

    for i, q in enumerate(latest):
        with db:
            c.execute(
                "INSERT INTO qso VALUES (:qso_date, :blog, :station, :directed_to,"
                " :frequency, :offset, :cmd, :rsp, :post_id, :post_date, :title, :body)",
                {
                    'qso_date': time.mktime(time.strptime(q['qso_date'], "%Y-%m-%d %H:%M:%S")),
                    'blog': q['blog'],
                    'station': q['station'],
                    'directed_to': q['directed_to'],
                    'frequency': q['frequency'],
                    'offset': q['offset'],
                    'cmd': q['cmd'],
                    'rsp': q['rsp'],
                    'post_id': q['post_id'],
                    'post_date': time.mktime(time.strptime(q['post_date'], "%Y-%m-%d %H:%M:%S")),
                    'title': q['title'],
                    'body': q['body'],
                }
            )

db.close()
