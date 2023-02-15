import tkinter as tk
import tkinter.font as font
import locale
import functools as ft
from settings import *
from status import *

root = tk.Tk()
root.title("Microblog Client r2")
root.geometry(settings.startup_dimensions)

font_btn = font.Font(family='Ariel', size=(int(settings.font_size*1.125)), weight='normal')
font_btn_bold = font.Font(family='Ariel', size=(int(settings.font_size*1.125)), weight='bold')
font_hdr = font.Font(family='Ariel', size=(int(settings.font_size*1.75)), weight='normal')
font_freq = font.Font(family='Seven Segment', size=(int(settings.font_size*3)), weight='normal')
font_main = font.Font(family='Ariel', size=settings.font_size, weight='normal')
font_main_ul = font.Font(family='Ariel', size=settings.font_size, weight='normal', underline=True)
font_main_hdr = font.Font(family='Ariel', size=(int(settings.font_size*1.25)), weight='normal')
font_main_bold = font.Font(family='Ariel', size=settings.font_size, weight='bold')


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

    def set_frequency(self):
        locale.setlocale(locale.LC_ALL, 'fr')
        field = [{'db_col': 'radio_frequency'}]
        status_table = DbTable('status')
        db_values = status_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=field
        )
        freq_str = locale.format_string("%d", db_values[0]['radio_frequency'], grouping=True)

        self.freq_text.set(freq_str)

    def set_offset(self):
        field = [{'db_col': 'offset'}]
        status_table = DbTable('status')
        db_values = status_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=field
        )

        self.offset_text.set(str(db_values[0]['offset']) + ' Hz')

    def set_callsign(self):
        field = [{'db_col': 'callsign'}]
        status_table = DbTable('status')
        db_values = status_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=field
        )

        self.callsign_text.set(db_values[0]['callsign'])


class GuiLatestPosts:

    latest_box = None

    latest_cols = [
        {'db_col': 'qso_date'},
        {'db_col': 'blog'},
        {'db_col': 'title'},
    ]

    def __init__(self, frame: tk.Frame):
        latest_list_hdr = tk.Label(
            frame,
            text="Latest Posts",
            bg='white',
            font=font_main_ul,
            justify=tk.LEFT,
            anchor=tk.W,
            padx=10, pady=12
        )
        latest_list_hdr.pack(anchor='ne', fill=tk.X)

        self.latest_box = tk.Text(
            frame, width=300, wrap=tk.WORD, padx=10, pady=5,
            font=font_main, bg='#ffffff',
            spacing1=1.1, spacing2=1.1,
            borderwidth=0
        )
        self.latest_box.pack(fill=tk.BOTH, expand=1, anchor='ne')

    def latest_reload(self):

        qso_table = DbTable('qso')
        db_values = qso_table.select(where=f"directed_to!='{status.callsign}'", order_by='qso_date', desc=True,
                                     limit=settings.max_latest, hdr_list=self.latest_cols)

        self.latest_box.configure(state=tk.NORMAL)
        self.latest_box.delete(1.0, 'end')

        for r in db_values:
            latest_string = ''

            q_date = time.strftime("%H:%M", time.gmtime(r['qso_date']))

            latest_string += f"{q_date} - {r['blog']}"
            latest_string += f" - {r['title']}"
            latest_string += f"\n"

            self.latest_box.insert(tk.END, latest_string)
            self.latest_box.see(tk.END)

        self.latest_box.configure(state=tk.DISABLED)
        return


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

        v = tk.Scrollbar(frame, orient='vertical')
        v.pack(side=tk.RIGHT, fill='y')
        self.qso_box = tk.Text(frame, width=480, wrap=tk.WORD, padx=10, pady=10,
                               font=font_main, bg='#ffeaa7', yscrollcommand=v.set,
                               spacing1=1.1, spacing2=1.1)
        v.config(command=self.qso_box.yview)
        self.qso_box.pack(fill=tk.BOTH, expand=1, anchor='ne')

    def qso_box_reload(self):

        qso_table = DbTable('qso')
        db_values = qso_table.select(where=f"directed_to='{status.callsign}'", order_by='qso_date', desc=False,
                                     limit=settings.max_qsos, hdr_list=self.qso_cols)

        self.qso_box.configure(state=tk.NORMAL)
        self.qso_box.delete(1.0, 'end')

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
    cli_text = None

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
        self.cli_hdr_text.set("Directed to:")

        self.cli_text = tk.Text(
            frame,
            font=font_main,
            width=50,
            height=1,
            padx=4,
            pady=4
        )
        self.cli_text.pack(fill=tk.X, padx=4, pady=4)

    def reload_cli(self):
        self.cli_hdr_text.set(f"Directed to: {status.selected_blog}")

    def clear_cli_input(self):
        self.cli_text.delete(1.0, tk.END)

    def set_selected_blog(self, blog: str):
        status.set_selected_blog(blog)
        self.reload_cli()


class GuiBlogList:

    blog_list = None  # this is a list of blog entries, each of which is a dictionary
    blog_list_headers = [
        {'db_col': 'blog_name', 'type': 'Text', 'suffix': '', 'width': 8,
         'text': 'Mblog', 'widget': None},
        {'db_col': 'station_name', 'type': 'Text', 'suffix': '', 'width': 8,
         'text': 'Station', 'widget': None},
        {'db_col': 'snr', 'type': 'Int', 'suffix': ' dB', 'width': 8,
         'text': 'SNR', 'widget': None},
        {'db_col': 'capabilities', 'type': 'Text', 'suffix': '', 'width': 8,
         'text': 'Cap.', 'widget': None},
        {'db_col': 'latest_post_date', 'type': 'Date', 'suffix': '', 'width': 14,
         'text': 'Latest\nPost Date', 'widget': None},
        {'db_col': 'latest_post_id', 'type': 'Int', 'suffix': '', 'width': 8,
         'text': 'Latest\nPost ID', 'widget': None},
        {'db_col': 'last_seen_date', 'type': 'Date', 'suffix': '', 'width': 14,
         'text': 'Last Seen', 'widget': None},
        {'db_col': 'is_selected', 'db_type': 'Int', 'suffix': '', 'width': 0,
         'text': None, 'widget': None},
    ]

    def __init__(self, frame):

        # construct the blog list grid
        self.blog_list = [[{} for _, _ in enumerate(self.blog_list_headers)] for _ in range(settings.max_blogs)]

        # initialise the blog list grid
        for row, _ in enumerate(self.blog_list):
            for col, blog in enumerate(self.blog_list[row]):
                blog['db_col'] = self.blog_list_headers[col]['db_col']
                blog['tv'] = None
                blog['widget'] = tk.Text()
                blog['selected'] = tk.FALSE

        # set the blog list columns to equal weight
        frame.grid(columnspan=len(self.blog_list_headers))
        for i, _ in enumerate(self.blog_list_headers):
            frame.columnconfigure(i, weight=1)

        # set the blog list headers
        for col, blog_hdr in enumerate(self.blog_list_headers):
            if blog_hdr['text']:
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

        # add the blog list Text widgets to the grid
        row = 0
        for row, _ in enumerate(self.blog_list):
            for col, blog in enumerate(self.blog_list[row]):
                if self.blog_list_headers[col]['text']:
                    blog['widget'] = tk.Text(
                        frame,
                        bg='white',
                        font=font_main,
                        relief=tk.FLAT,
                        width=self.blog_list_headers[col]['width'],
                        height=1,
                        padx=10
                    )
                    blog['widget'].grid(column=col, row=row + 1)  # need to row+1 to allow for header

            row = row + 1

    def blog_list_reload(self):
        # clear all entries
        for row, _ in enumerate(self.blog_list):
            for col, blog in enumerate(self.blog_list[row]):
                blog['widget'].configure(state=tk.NORMAL)
                blog['widget'].delete(1.0, tk.END)

        blogs_table = DbTable('blogs')
        db_values = blogs_table.select(order_by='last_seen_date', desc=True, limit=30,
                                       hdr_list=self.blog_list_headers)

        for row, db_row in enumerate(db_values):
            for col, col_name in enumerate(list(db_row)):
                if col_name == 'is_selected':  # this marks the end of the list, and we don't add it to the grid
                    break

                if self.blog_list_headers[col]['type'] == 'Int':
                    value = str(db_row[col_name]) + self.blog_list_headers[col]['suffix']
                elif self.blog_list_headers[col]['type'] == 'Date':
                    value = time.strftime("%Y-%m-%d %H:%M", time.gmtime(db_row[col_name]))\
                            + self.blog_list_headers[col]['suffix']
                else:
                    value = db_row[col_name] + self.blog_list_headers[col]['suffix']

                blog_cell = self.blog_list[row][col]
                blog_cell['widget'].tag_configure('tag_all', justify='center')
                blog_cell['widget'].insert('1.0', value)
                blog_cell['widget'].tag_add('tag_all', '1.0', tk.END)
                blog_cell['widget'].tag_bind('tag_all', '<Button-1>',
                                             ft.partial(self.select_blog, param=row))
                if db_row['is_selected']:  # check the selected flag
                    blog_cell['widget'].configure(bg='#3498db', fg='#000000')
                blog_cell['widget'].configure(state=tk.DISABLED)

        return

    def select_blog(self, event, param):
        pass  ### write this next

class GuiMain:

    def __init__(self, frame):
        pane_main = tk.PanedWindow(frame, bg='#606060')
        pane_main.pack(fill='both', expand=1, side='top')

        frame_left = tk.Frame(pane_main, bg='white')
        pane_main.add(frame_left, width=300)

        frame_mid = tk.Frame(pane_main, bg='white')
        pane_main.add(frame_mid, width=480)

        frame_right = tk.Frame(pane_main, bg='white')
        pane_main.add(frame_right, width=300)

        # Latest Posts area
        frame_latest_list = tk.Frame(frame_left, bg='white')
        frame_latest_list.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.latest_posts = GuiLatestPosts(frame_latest_list)

        # QSO Area follows - middle of main
        frame_qso = tk.Frame(frame_mid)
        frame_qso.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.qso_box = GuiQsoBox(frame_qso)

        frame_cli = tk.Frame(frame_mid)
        frame_cli.pack(side=tk.BOTTOM, padx=4)

        self.cli = GuiCli(frame_mid)

        # Blog list area - right of main
        frame_blog_list = tk.Frame(frame_right, bg='white', padx=4, pady=4)
        frame_blog_list.pack()

        self.blog_list = GuiBlogList(frame_blog_list)

    def latest_reload(self):
        self.latest_posts.latest_reload()

    def set_selected_blog(self, blog: str):
        self.cli.set_selected_blog(blog)

    def qso_box_reload(self):
        self.qso_box.qso_box_reload()

    def blog_list_reload(self):
        self.blog_list.blog_list_reload()
