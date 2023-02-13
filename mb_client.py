import tkinter as tk
from tkinter import ttk
import tkinter.font as font
import time
from settings import *
import sqlite3

max_post_list = 30
max_qsos = 50
max_blogs = 30

root = tk.Tk()
root.title("Microblog Client r2")
root.geometry("1080x640")

font_btn = font.Font(family='Ariel', size=9, weight='normal')
font_btn_bold = font.Font(family='Ariel', size=9, weight='bold')
font_hdr = font.Font(family='Ariel', size=14, weight='normal')
font_freq = font.Font(family='Seven Segment', size=24, weight='normal')
font_main = font.Font(family='Ariel', size=8, weight='normal')
font_main_ul = font.Font(family='Ariel', size=8, weight='normal', underline=True)
font_main_hdr = font.Font(family='Ariel', size=10, weight='normal')
font_main_bold = font.Font(family='Ariel', size=8, weight='bold')


class Timeout:
    target_time = 0
    timeout_value = 0

    def __init__(self, to_in_secs: int):
        self.to_value = to_in_secs

    def start(self):
        self.target_time = time.time() + self.timeout_value

    def has_expired(self) -> bool:
        if time.time() > self.target_time:
            return True
        else:
            return False


class DbTable:

    col_names = None
    result = None
    has_is_selected = False

    def __init__(self, table):
        self.table = table

        db = sqlite3.connect(db_file)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute(f"SELECT * FROM {table} LIMIT 1")
        row = c.fetchone()
        self.col_names = row.keys()
        if 'is_selected' in self.col_names:
            self.has_is_selected = True

        c.close()

    # This method returns a list of dictionaries with the columns selected by the
    # hdr_list, in the order of the columns in the hdr_list.
    # The hdr_list must contain a key db_col with a value of the name of a database column.
    def select(self, where=None, order_by=None, desc=False, limit=0, hdr_list=None):

        db = sqlite3.connect(db_file)
        c = db.cursor()

        select_cols = ''
        for i, hdr_col in enumerate(hdr_list):
            if i > 0:
                select_cols += ','
            select_cols += f" {hdr_col['db_col']}"

        query = f"SELECT {select_cols} FROM {self.table}"
        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if desc:
            query += f" DESC"
        if limit > 0:
            query += f" LIMIT {limit}"

        c.execute(query)
        list_of_tuples = c.fetchall()
        db.close()

        result = [{} for _ in range(0, len(list_of_tuples))]

        # convert the list of tuples to a list of dictionaries based on the self.col_names values
        for y, row in enumerate(list_of_tuples):
            for x, col in enumerate(hdr_list):
                abc = f"{col['db_col']}"
                result[y][abc] = row[x]

        return result


class ScrollableFrame(ttk.Frame):  # ToDo: rewrite this class so that it expands correctly
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)

        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class GuiHeader:

    js8_freqs = [1.842, 3.578, 7.078, 10.130, 14.078, 18.104, 21.078, 24.922, 27.245, 28.078, 50.318]

    is_scanning = False
    freq_text = tk.StringVar()
    offset_text = tk.StringVar()
    callsign_text = tk.StringVar()
    scan_btn = None
    clock_label = None

    def __init__(self, header_frame):
        frame_hdr_left = tk.Frame(header_frame, bg='black')
        frame_hdr_left.pack(expand=True, fill='y', side='left')
        frame_hdr_mid = tk.Frame(header_frame, bg='black')
        frame_hdr_mid.pack(expand=True, fill='y', side='left')
        frame_hdr_right = tk.Frame(header_frame, bg='black')
        frame_hdr_right.pack(expand=True, fill='y', side='left')

        frame_cell_1 = tk.Frame(frame_hdr_left, bg='black')
        frame_cell_1.pack(expand=True, fill='both')
        # frequency in the header
        hdr_freq = tk.Label(
            frame_cell_1,
            textvariable=self.freq_text,
            bg='black', fg='white',
            font=font_freq,
            justify='center',
        )
        hdr_freq.pack()

        frame_cell_4 = tk.Frame(frame_hdr_left, bg='black')
        frame_cell_4.pack(expand=True, fill='both')
        hdr_offset = tk.Label(
            frame_cell_4,
            textvariable=self.offset_text,
            bg='black', fg='white',
            font=font_hdr,
            justify='center',
        )
        hdr_offset.pack()

        # Callsign
        frame_cell_2 = tk.Frame(frame_hdr_mid, bg='black')
        frame_cell_2.pack(expand=True, fill='both')
        hdr_callsign = tk.Label(
            frame_cell_2,
            textvariable=self.callsign_text,
            bg='black', fg='white',
            font=font_hdr
        )
        hdr_callsign.pack()

        # Clock
        frame_cell_5 = tk.Frame(frame_hdr_mid, bg='black')
        frame_cell_5.pack(expand=True, fill='both')
        self.clock_label = tk.Label(
            frame_cell_5,
            bg='black', fg='white',
            font=font_hdr,
        )
        self.clock_label.pack()

        # Scan button
        frame_cell_3 = tk.Frame(frame_hdr_right, bg='black')
        frame_cell_3.pack(expand=True, fill='both')
        self.scan_btn = tk.Button(
            frame_cell_3,
            text='Scan',
            font=font_btn_bold,
            bg='#22ff23', height=1, width=18,
            relief='flat',
            command=self.toggle_scan
        )
        self.scan_btn.pack()

        # Blank Cell
        frame_cell_6 = tk.Frame(frame_hdr_right, bg='black')
        frame_cell_6.pack(expand=True, fill='both')
        hdr_blank = tk.Label(
            frame_cell_6,
            text='',
            bg='black', fg='white',
            font=font_hdr
        )
        hdr_blank.pack()

    def clock_tick(self, curtime=''):  # used for the header clock
        newtime = time.strftime('%Y-%m-%d %H:%M:%S')
        if newtime != curtime:
            curtime = newtime
            self.clock_label.config(text=curtime)
        self.clock_label.after(200, self.clock_tick, curtime)

    def toggle_scan(self):
        if self.is_scanning:
            self.is_scanning = False
            self.scan_btn.configure(bg='#22ff23')
        else:
            self.is_scanning = True
            self.scan_btn.configure(bg='#ff2222')

    def set_frequency(self, freq):
        self.freq_text.set(freq)

    def set_offset(self, offset):
        self.offset_text.set(offset)

    def set_callsign(self, callsign):
        self.callsign_text.set(callsign)


class GuiLatestPosts:
    latest_post_list = []
    latest_btn_list = []

    def __init__(self, frame):
        global max_post_list
        latest_list_hdr = tk.Label(
            frame,
            text="Latest Posts",
            bg='white',
            font=font_main_ul,
            justify=tk.LEFT,
            anchor=tk.W,
            padx=4
        )
        latest_list_hdr.pack(anchor='ne', fill=tk.X)

        for i in range(0, max_post_list):
            self.latest_post_list.append(tk.StringVar())

        for index in range(0, max_post_list):
            self.latest_btn_list.append(
                tk.Button(
                    frame,
                    textvariable=self.latest_post_list[index],
                    font=font_main,
                    activebackground='#f0f0f0',
                    bg='white',
                    height=1,
                    anchor=tk.W,
                    padx=4,
                    pady=3,
                    relief='flat'
                )
            )
            self.latest_btn_list[-1].pack(anchor='ne', fill=tk.X)

    def prepend_latest(self, post_line: str):
        list_length = len(self.latest_post_list)
        for index in range(list_length - 1, 0, -1):  # index starts by addressing the last entry
            self.latest_post_list[index].set(self.latest_post_list[index - 1].get())
        self.latest_post_list[0].set(post_line)


# class GuiQsoBox:
#
#     qso_text = []
#     qso_label = []
#     qso_cols = [
#         {'db_col': 'qso_date'},
#         {'db_col': 'blog'},
#         {'db_col': 'cmd'},
#         {'db_col': 'rsp'},
#         {'db_col': 'post_id'},
#         {'db_col': 'post_date'},
#         {'db_col': 'title'},
#         {'db_col': 'body'},
#     ]
#
#     def __init__(self, frame: tk.Frame):
#
#         self.qso_frame = frame
#
#         # ok - I'm not proud of this, but I have tried everything I can think of to get the scrollable
#         # frame to expand
#         junk_text = "\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t"
#         junk = tk.Label(
#             frame.scrollable_frame,
#             text=junk_text,
#             bg='#ffeaa7',
#             font=font_main,
#             justify=tk.LEFT,
#             anchor=tk.W,
#             padx=4,
#             pady=3,
#         )
#         junk.pack(fill=tk.X, expand=1, anchor='ne')
#
#         global max_qsos
#         for i in range(0, max_qsos):
#             self.qso_text.append(tk.StringVar())
#
#         for index in range(0, max_qsos):
#             self.qso_label.append(
#                 tk.Label(
#                     frame.scrollable_frame,
#                     textvariable=self.qso_text[index],
#                     font=font_main,
#                     bg='#ffeaa7',
#                     anchor=tk.W,
#                     justify=tk.LEFT,
#                     wraplength=360,
#                     padx=10,
#                     pady=3, relief='flat'
#                 )
#             )
#             self.qso_label[-1].pack(anchor='ne', fill=tk.X)
#
#
#     def append_qso(self, value: str):
#         list_length = len(self.qso_text)
#         for index in range(list_length - 1, 0, -1):  # index starts by addressing the last entry
#             self.qso_text[index - 1].set(self.qso_text[index].get())
#         self.qso_text[list_length - 1].set(value)
#
#     def qso_box_reload(self):
#         # initialise the text of off the labels
#         for i in range(0, len(self.qso_text)):
#             self.qso_text[i].set('')
#
#         qso_table = DbTable('qso')
#         db_values = qso_table.select(order_by='qso_date', desc=False, limit=max_qsos, hdr_list=self.qso_cols)
#         qso_string = ''
#
#         for i, r in enumerate(db_values):
#             if r['rsp'] == 'OK' and len(r['body']) > 0:
#                 # it's a post entry
#                 q_date = time.strftime("%H:%M", time.gmtime(r['qso_date']))
#                 if r['post_date'] > 0:
#                     p_date = time.strftime("%Y-%m-%d", time.gmtime(r['post_date']))
#                 else:
#                     p_date = None
#
#                 qso_string = f"{q_date} | Blog: {r['blog']} | Post ID: {r['post_id']}"
#                 if p_date:
#                     qso_string += f" | Post Date: {p_date}"
#                 if len(r['title']):
#                     qso_string += f" | Title: {r['title']}"
#                 qso_string += f"\n\n{r['body']}"
#
#                 self.qso_text[i].set(qso_string)
#
#         return


class GuiQsoBox:

    qso_box = []

    prev_is_listing = False

    qso_cols = [
        {'db_col': 'qso_date'},
        {'db_col': 'blog'},
        {'db_col': 'cmd'},
        {'db_col': 'rsp'},
        {'db_col': 'post_id'},
        {'db_col': 'post_date'},
        {'db_col': 'title'},
        {'db_col': 'body'},
    ]

    def __init__(self, frame: tk.Frame):

        self.qso_box = tk.Text(frame, width=400, wrap=tk.WORD, padx=10, pady=10, font=font_main, bg='#ffeaa7')
        self.qso_box.pack(fill=tk.BOTH, expand=1, anchor='ne')


    def append_qso(self, value: str):
        self.qso_box.insert(tk.END, value)

    def qso_box_reload(self):

        qso_table = DbTable('qso')
        db_values = qso_table.select(order_by='qso_date', desc=False, limit=max_qsos, hdr_list=self.qso_cols)

        self.qso_box.configure(state=tk.NORMAL)
        self.qso_box.delete(1.0, 'end')

        qso_string = ''

        for i, r in enumerate(db_values):
            if r['rsp'] == 'OK' and len(r['body']) > 0:
                # it's a post entry
                qso_string = "\n----------------------------------------------\n"
                q_date = time.strftime("%H:%M", time.gmtime(r['qso_date']))
                if r['post_date'] > 0:
                    p_date = time.strftime("%Y-%m-%d", time.gmtime(r['post_date']))
                else:
                    p_date = None

                qso_string += f"{q_date} {r['blog']} #{r['post_id']}"
                if p_date:
                    qso_string += f" {p_date}"
                if len(r['title']):
                    qso_string += f" {r['title']}"
                qso_string += f"\n\n{r['body']}"

                self.qso_box.insert(tk.END, qso_string)
                self.qso_box.see(tk.END)
                self.prev_is_listing = False

            elif r['rsp'] == 'OK' and len(r['body']) == 0:
                # it's a listing
                qso_string = ''
                if not self.prev_is_listing:
                    qso_string = "\n----------------------------------------------\n"
                q_date = time.strftime("%H:%M", time.gmtime(r['qso_date']))
                if r['post_date'] > 0:
                    p_date = time.strftime("%Y-%m-%d", time.gmtime(r['post_date']))
                else:
                    p_date = None

                qso_string += f"{q_date} {r['blog']} #{r['post_id']}"
                if p_date:
                    qso_string += f" {p_date}"

                qso_string += f" {r['title']}\n"

                self.qso_box.insert(tk.END, qso_string)
                self.qso_box.see(tk.END)
                self.prev_is_listing = True

        self.qso_box.configure(state=tk.DISABLED)
        return

class GuiCli:

    cli_hdr_text = tk.StringVar()

    def __init__(self, frame):

        cli_hdr = tk.Label(frame,
                           textvariable=self.cli_hdr_text,
                           bg='#000000',
                           fg='#ffffff',
                           font=font_main,
                           justify=tk.LEFT,
                           anchor=tk.W,
                           padx=4,
                           pady=3,
                           )
        cli_hdr.pack(fill=tk.X, anchor=tk.W, padx=4, pady=4)
        self.cli_hdr_text.set("Directed to: Nowhere")

        cli_text = tk.Text(
            frame,
            font=font_main,
            width=50,
            height=1,
            padx=4,
            pady=4
        )
        cli_text.pack(fill=tk.X, padx=4, pady=4)

    def set_selected_blog(self, blog: str):
        self.cli_hdr_text.set(f"Directed to: {blog}")


class GuiBlogList:

    blog_list = None  # this is a list of blog entries, each of which is a dictionary
    blog_list_headers = None  # this is a list of blog list headers, each of which is a dictionary
    blog_list_headers = [
        {'db_col': 'blog_name', 'type': 'Text', 'suffix': '', 'text': 'Mblog', 'widget': tk.Button()},
        {'db_col': 'station_name', 'type': 'Text', 'suffix': '', 'text': 'Station', 'widget': tk.Button()},
        {'db_col': 'snr', 'type': 'Int', 'text': 'SNR', 'suffix': ' dB', 'widget': tk.Button()},
        {'db_col': 'capabilities', 'type': 'Text', 'suffix': '', 'text': 'Cap.', 'widget': tk.Button()},
        {'db_col': 'latest_post_date', 'type': 'Date', 'suffix': '', 'text': 'Latest\nPost Date',
         'widget': tk.Button()},
        {'db_col': 'latest_post_id', 'type': 'Int', 'suffix': '', 'text': 'Latest\nPost ID', 'widget': tk.Button()},
        {'db_col': 'last_seen_date', 'type': 'Date', 'suffix': '', 'text': 'Last Seen', 'widget': tk.Button()},
        {'db_col': 'is_selected', 'db_type': 'Int', 'suffix': '', 'text': None, 'widget': None},
    ]

    def __init__(self, frame):
        global max_blogs

        self.blog_list = [[{} for _, _ in enumerate(self.blog_list_headers)] for _ in range(max_blogs)]

        for row, _ in enumerate(self.blog_list):
            for col, blog in enumerate(self.blog_list[row]):
                blog['db_col'] = self.blog_list_headers[col]['db_col']
                blog['tv'] = tk.StringVar()
                blog['widget'] = tk.Button()
                blog['selected'] = tk.FALSE

        frame.grid(columnspan=len(self.blog_list_headers))
        for i, _ in enumerate(self.blog_list_headers):
            frame.columnconfigure(i, weight=1)

        # set the headers
        for col, blog_hdr in enumerate(self.blog_list_headers):
            blog_hdr['widget'] = tk.Button(
                frame,
                text=self.blog_list_headers[col]['text'],
                relief='flat',
                bg='white',
                font=font_main_ul,
                justify=tk.CENTER,
                anchor=tk.W
            )
            blog_hdr['widget'].grid(row=0, column=col)

        # add the blog list buttons to the grid
        row = 0
        for _ in self.blog_list:
            for col, blog in enumerate(self.blog_list[row]):
                blog['widget'] = tk.Button(
                    frame,
                    textvariable=self.blog_list[row][col]['tv'],
                    bg='white',
                    font=font_main,
                    justify=tk.CENTER,
                    relief=tk.FLAT,
                    width=14
                )
                blog['widget'].grid(column=col, row=row + 1)  # need to row+1 to allow for header

            row = row + 1

    def blog_list_reload(self):
        # clear all entries
        for row, _ in enumerate(self.blog_list):
            for col, blog in enumerate(self.blog_list[row]):
                blog['tv'].set(value='')
                blog['widget'].configure(bg='#ffffff')

        blogs_table = DbTable('blogs')
        db_values = blogs_table.select(order_by='last_seen_date', desc=True, limit=30, hdr_list=self.blog_list_headers)

        for row, db_row in enumerate(db_values):
            for col, col_name in enumerate(list(db_row)):
                if col_name == 'is_selected':  # this marks the end of the list and we don't add it to the grid
                    break

                if self.blog_list_headers[col]['type'] == 'Int':
                    value = str(db_row[col_name]) + self.blog_list_headers[col]['suffix']
                elif self.blog_list_headers[col]['type'] == 'Date':
                    value = time.strftime("%Y-%m-%d %H:%M", time.gmtime(db_row[col_name]))\
                            + self.blog_list_headers[col]['suffix']
                else:
                    value = db_row[col_name] + self.blog_list_headers[col]['suffix']

                blog_cell = self.blog_list[row][col]
                blog_cell['tv'].set(value)
                if db_row['is_selected']:  # check the selected flag
                    blog_cell['widget'].configure(bg='#3498db')
                    blog_cell['widget'].configure(fg='#000000')
        return


class GuiMain:

    def __init__(self, frame):
        pane_main = tk.PanedWindow(frame, bg='#606060')
        pane_main.pack(fill='both', expand=1, side='top')

        frame_left = tk.Frame(pane_main, bg='white')
        pane_main.add(frame_left)

        frame_mid = tk.Frame(pane_main, bg='white')
        pane_main.add(frame_mid, width=440)

        frame_right = tk.Frame(pane_main, bg='white')
        pane_main.add(frame_right)

        # Latest Posts area
        frame_latest_list = tk.Frame(frame_left, bg='white')
        frame_latest_list.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.latest_posts = GuiLatestPosts(frame_latest_list)

        # QSO Area follows - middle of main
        frame_qso_outer = tk.Frame(frame_mid, width=480)
        frame_qso_outer.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # frame_qso = ScrollableFrame(frame_qso_outer)
        # frame_qso.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=4)

        self.qso_box = GuiQsoBox(frame_qso_outer)

        frame_cli = tk.Frame(frame_mid)
        frame_cli.pack(side=tk.BOTTOM, padx=4)

        self.cli = GuiCli(frame_mid)

        # Blog list area - right of main
        frame_blog_list = tk.Frame(frame_right, bg='white', padx=4, pady=4)
        frame_blog_list.pack()

        self.blog_list = GuiBlogList(frame_blog_list)

    def prepend_latest(self, value: str):
        self.latest_posts.prepend_latest(value)

    def set_selected_blog(self, blog: str):
        self.cli.set_selected_blog(blog)

    def qso_box_reload(self):
        self.qso_box.qso_box_reload()

    def blog_list_reload(self):
        self.blog_list.blog_list_reload()


# Code here is first to run
frame_container = tk.Frame(root)
frame_container.pack(fill='x', expand=1, side='top', anchor='n')

frame_hdr = tk.Frame(frame_container, background="black", height=100, pady=10)
frame_hdr.pack(fill='x', expand=1, side='top', anchor='n')
header = GuiHeader(header_frame=frame_hdr)  # populate the header

frame_main = tk.Frame(frame_container, pady=4)
frame_main.pack(fill='both', expand=1, side='top', anchor='n', padx=4)

# Now for the logic

header.set_frequency('14.078 000')
header.set_offset('1800 Hz')
header.set_callsign('2E0FGO')
header.clock_tick()

main = GuiMain(frame=frame_main)  # populate the main area

main.prepend_latest("2023-02-03 08:30 - K7RA Solar Update")
main.prepend_latest("2023-02-07 11:04 - EmComms Due to Earthquake in Turkey")

main.set_selected_blog('M0PXO')

main.qso_box_reload()

main.blog_list_reload()


root.mainloop()
