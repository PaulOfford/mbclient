import queue
import tkinter as tk
import tkinter.font as font
import locale
import functools as ft
import re

from _version import __version__
from settings import *
from message_q import *

root = tk.Tk()
window_title = "Microblog Client " + __version__
root.title(window_title)
root.geometry(settings.startup_dimensions)

font_btn = font.Font(family='Ariel', size=(int(settings.font_size*1.125)), weight='normal')
font_btn_bold = font.Font(family='Ariel', size=(int(settings.font_size*1.125)), weight='bold')
font_hdr = font.Font(family='Ariel', size=(int(settings.font_size*1.75)), weight='normal')
font_freq = font.Font(family='Seven Segment', size=(int(settings.font_size*3)), weight='normal')
font_main = font.Font(family='Ariel', size=settings.font_size, weight='normal')
font_main_ul = font.Font(family='Ariel', size=settings.font_size, weight='normal', underline=True)
font_main_hdr = font.Font(family='Ariel', size=(int(settings.font_size*1.25)), weight='normal')
font_main_bold = font.Font(family='Ariel', size=settings.font_size, weight='bold')


def settings_window():
    sw = tk.Tk()
    sw.title("Settings")
    sw.geometry("400x320")

    label_list = [
        ('startup_width', 'Window Startup Width:', 'entry', tk.IntVar(sw)),
        ('startup_height', 'Window Startup Height:', 'entry', tk.IntVar(sw)),
        ('font_size', 'Font Size:', 'entry', tk.IntVar(sw)),
        ('max_latest', 'Max Latest:', 'entry', tk.IntVar(sw)),
        ('max_qsos', 'Max QSOs:', 'entry', tk.IntVar(sw)),
        ('max_blogs', 'Max Blogs:', 'entry', tk.IntVar(sw)),
        ('max_listing', 'Max Listing:', 'entry', tk.IntVar(sw)),
        ('use_gmt', 'Use GMT for Clock and Log:', 'checkbox', tk.IntVar(sw)),
    ]
    entry_list = []

    # Row and Column configure to manage weights
    sw.columnconfigure(0, weight=1)
    sw.columnconfigure(2, weight=1)
    sw.rowconfigure(0, weight=1)
    sw.rowconfigure(2, weight=1)

    # Add a frame to hold the rest of the widgets and place that frame in the row/column without a weight.
    # This will allow us to center everything that we place in the frame.
    sw_frame = tk.Frame(sw)
    sw_frame.grid(row=1, column=1)

    # create the labels and entry widgets
    for i, label in enumerate(label_list):
        tk.Label(sw_frame, text=label[1] + ' ', font='8').grid(row=i, column=0, sticky='w')
        # Store the entry widgets in a list for later use
        if label[2] == 'entry':
            entry_list.append(tk.Entry(sw_frame, borderwidth=2, width=8, font='8', relief=tk.GROOVE))
            entry_list[-1].grid(row=i, column=1)
            entry_list[-1].insert(0, settings.get_setting(label[0]))
        elif label[2] == 'checkbox':
            entry_list.append(
                tk.Checkbutton(
                    sw_frame, justify='left', onvalue=1, offvalue=0, variable=label[3]
                )
            )
            entry_list[-1].grid(row=i, column=1)
            if settings.get_setting(label[0]) == 1:
                entry_list[-1].select()
            pass

    # save the settings
    def save_entries():
        for j, entry in enumerate(entry_list):
            my_label = label_list[j]
            if entry.widgetName == 'entry':
                settings.set_setting(my_label[0], entry.get())
            elif entry.widgetName == 'checkbutton':
                print(my_label[3].get())
                if my_label[3].get():
                    db_value = 1
                else:
                    db_value = 0
                settings.set_setting(my_label[0], db_value)
        sw.destroy()

    tk.Label(sw_frame, text=' ').grid(row=len(label_list)+1, column=0, columnspan=2)
    tk.Button(
        sw_frame, text='Cancel', font='8', command=sw.destroy
    ).grid(row=len(label_list)+2, column=0)
    tk.Button(
        sw_frame, text='Save', font='8', command=save_entries
    ).grid(row=len(label_list)+2, column=1)


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

        self.reload_header()

    def clock_tick(self, curtime=''):  # used for the header clock
        if settings.use_gmt:
            newtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        else:
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
        field = ['radio_frequency']
        status_table = DbTable('status')
        db_values = status_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=field
        )
        locale.setlocale(locale.LC_ALL, 'fr')
        freq_str = locale.format_string("%d", db_values[0]['radio_frequency'], grouping=True)
        locale.setlocale(locale.LC_ALL, 'en_GB')

        self.freq_text.set(freq_str)

    def set_offset(self):
        field = ['offset']
        status_table = DbTable('status')
        db_values = status_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=field
        )

        self.offset_text.set(str(db_values[0]['offset']) + ' Hz')

    def set_callsign(self):
        field = ['callsign']
        status_table = DbTable('status')
        db_values = status_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=field
        )

        self.callsign_text.set(db_values[0]['callsign'])

    def reload_header(self):
        self.set_frequency()
        self.set_offset()
        self.set_callsign()


class GuiLatestPosts:

    f2b_q = None
    latest_box = None
    latest_cols = ['post_id', 'qso_date', 'blog', 'station', 'frequency', 'title']

    def __init__(self, frame: tk.Frame, f2b_q: queue.Queue):

        self.f2b_q = f2b_q

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

        self.reload_latest()

    def get_post(self, blog: str, station: str, frequency: int, post_id: int, event):

        req = GuiMessage()

        req.set_blog(blog)
        req.set_station(station)
        req.set_frequency(frequency)
        req.set_cli_input(f'G {post_id}')
        req.set_cmd('G')
        req.set_op('eq')
        req.set_post_id(post_id)
        req.set_post_date(0)
        req.set_ts()
        self.f2b_q.put(req)
        logging.logmsg(3, f"fe: {req}")

    def reload_latest(self):

        status = Status()

        qso_table = DbTable('qso')
        db_values = qso_table.select(
            where=f"directed_to!='{status.callsign}' AND title IS NOT ''",
            group_by='post_id',
            order_by='qso_date',
            desc=True,
            limit=settings.max_latest,
            hdr_list=self.latest_cols
        )

        self.latest_box.configure(state=tk.NORMAL)
        self.latest_box.delete(1.0, 'end')

        for i, r in enumerate(db_values):
            latest_string = ''

            q_date = time.strftime("%H:%M", time.gmtime(r['qso_date']))

            latest_string += f"{q_date} - {r['blog']}"
            latest_string += f" - {r['title']}"
            latest_string += f"\n"

            tag_name = 'tag_latest_row_' + str(i)

            self.latest_box.tag_configure(tag_name, justify='left')
            self.latest_box.insert(tk.END, latest_string)
            self.latest_box.see(tk.END)
            coords_start = f'{i+1}.0'
            coords_end = f'{i+1}.{len(latest_string)}'
            self.latest_box.tag_add(tag_name, coords_start, coords_end)
            self.latest_box.tag_bind(
                tag_name, '<Button-1>',
                ft.partial(self.get_post, r['blog'], r['station'], r['frequency'], r['post_id'])
            )

        self.latest_box.configure(state=tk.DISABLED)
        return


class GuiQsoBox:

    qso_box = []

    prev_is_listing = False

    qso_cols = ['qso_date', 'type', 'blog', 'station', 'cmd', 'rsp', 'post_id', 'post_date', 'title',
                'body']

    def __init__(self, frame: tk.Frame):

        v = tk.Scrollbar(frame, orient='vertical')
        v.pack(side=tk.RIGHT, fill='y')
        self.qso_box = tk.Text(frame, width=480, wrap=tk.WORD, padx=10, pady=10,
                               font=font_main, bg='#ffeaa7', yscrollcommand=v.set,
                               spacing1=1.1, spacing2=1.1)
        v.config(command=self.qso_box.yview)
        self.qso_box.pack(fill=tk.BOTH, expand=1, anchor='ne')

    def reload_qso_box(self):

        status = Status()

        qso_table = DbTable('qso')
        db_values = qso_table.select_latest(
            where=f"directed_to='{status.callsign}'", order_by='qso_date',
            limit=settings.max_qsos, hdr_list=self.qso_cols
        )

        self.qso_box.configure(state=tk.NORMAL)
        self.qso_box.delete(1.0, 'end')

        for i, r in enumerate(db_values):
            if r['type'] == 'post':
                # it's a post entry
                qso_string = ''

                q_date = time.strftime("%H:%M", time.gmtime(r['qso_date']))
                if r['post_date'] > 0:
                    p_date = time.strftime("%Y-%m-%d", time.gmtime(r['post_date']))
                else:
                    p_date = None

                qso_string += f"\n{q_date} {r['blog']} +{r['cmd']}"
                if p_date:
                    qso_string += f" {p_date}"
                if len(r['title']):
                    qso_string += f" {r['title']}"
                qso_string += f"\n\n{r['body']}\n"

                self.qso_box.insert(tk.END, qso_string)
                self.qso_box.see(tk.END)
                self.prev_is_listing = False

            elif r['type'] == 'listing':
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

            elif r['type'] == 'cmd':
                # it's an echoed command
                qso_string = ''
                q_date = time.strftime("%H:%M", time.gmtime(r['qso_date']))
                qso_string += f"\n{q_date} {r['blog']} {r['cmd']} {r['rsp']}\n"
                self.qso_box.insert(tk.END, qso_string)
                self.qso_box.see(tk.END)
                self.prev_is_listing = True

            elif r['type'] == 'progress':
                # it's an echoed command
                qso_string = ''
                q_date = time.strftime("%H:%M", time.gmtime(r['qso_date']))
                qso_string += f"{q_date} {r['blog']} {r['cmd']} {r['rsp']}\n"
                self.qso_box.insert(tk.END, qso_string)
                self.qso_box.see(tk.END)
                self.prev_is_listing = True

        self.qso_box.configure(state=tk.DISABLED)
        return


class GuiCli:

    cli_hdr_text = tk.StringVar()
    cli_text = None

    input_is_valid = False

    def __init__(self, frame, f2b_q: queue.Queue):

        self.f2b_q = f2b_q

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

        self.cli_text = tk.Entry(
            frame,
            font=font_main,
            width=50,
        )
        self.cli_text.bind('<Key>', self.go_cli)
        self.cli_text.pack(fill=tk.X, padx=4, pady=4)
        self.reload_cli()

    def reload_cli(self):
        status = Status()
        self.cli_hdr_text.set(f"Directed to: {status.selected_blog}")
        self.cli_text.focus_set()

    def clear_cli_input(self):
        self.cli_text.delete(0, tk.END)

    def set_error(self):
        self.cli_text.config({"background": "Pink"})

    def go_cli(self, event):

        req = GuiMessage()

        command_informat = [
            {'exp': '^L *(\\d+)$', 'op': 'eq', 'by': 'id'},
            {'exp': '^L *> *(\\d+)$', 'op': 'gt', 'by': 'id'},
            {'exp': '^L *(\\d{4}-\\d{2}-\\d{2})$', 'op': 'eq', 'by': 'date'},
            {'exp': '^L *> *(\\d{4}-\\d{2}-\\d{2})$', 'op': 'gt', 'by': 'date'},
            {'exp': '^L$', 'op': 'tail', 'by': None},

            {'exp': '^E *(\\d+)$', 'op': 'eq', 'by': 'id'},
            {'exp': '^E *> *(\\d+)$', 'op': 'gt', 'by': 'id'},
            {'exp': '^E *(\\d{4}-\\d{2}-\\d{2})$', 'op': 'eq', 'by': 'date'},
            {'exp': '^E *> *(\\d{4}-\\d{2}-\\d{2})$', 'op': 'gt', 'by': 'date'},
            {'exp': '^E$', 'op': 'tail', 'by': None},

            {'exp': '^G *(\\d+)$', 'op': 'eq', 'by': 'id'},
        ]

        entry = None
        result = None

        self.cli_text.config({"background": "White"})

        # check keystroke, if it's an Enter process else return
        if event.char == '\r' and event.keysym == "Return":
            self.input_is_valid = False
            # get the text from the cli box
            # shift to upper text and strip whitespace from start and end
            input_text = self.cli_text.get().upper().strip()
            # parse input using regex
            for entry in command_informat:
                # try to match the request
                result = re.findall(entry['exp'], input_text)

                if len(result) > 0:
                    self.input_is_valid = True
                    break
                else:
                    continue

            if self.input_is_valid:
                status = Status()
                # send message to backend
                req.set_blog(status.selected_blog)
                req.set_station(status.selected_station)
                req.set_cli_input(input_text)
                req.set_cmd(input_text[0:1])
                req.set_op(entry['op'])

                if entry['by'] == 'id':
                    req.set_post_id(int(result[0]))
                elif entry['by'] == 'date':
                    if len(result[0]) > 0:
                        epoch_dt = int(time.mktime(time.strptime(result[0], "%Y-%m-%d")))
                    else:
                        epoch_dt = 0
                    req.set_post_date(epoch_dt)
                # else must be a tail

                req.set_ts()
                self.f2b_q.put(req)
                logging.logmsg(3, f"fe: {req}")
                # clear the text box
                self.clear_cli_input()
            else:
                # turn cli box red if input is no good
                self.set_error()

        return


class GuiBlogList:

    blog_list = None  # this is a list of blog entries, each of which is a dictionary
    blog_list_headers = [
        {'db_col': 'blog', 'type': 'Text', 'suffix': '', 'width': 8,
         'text': 'Mblog', 'widget': tk.Button()},
        {'db_col': 'station', 'type': 'Text', 'suffix': '', 'width': 8,
         'text': 'Station', 'widget': tk.Button()},
        {'db_col': 'frequency', 'type': 'Float', 'divisor': 1000000, 'suffix': ' MHz', 'width': 12,
         'text': 'Freq', 'widget': tk.Button()},
        {'db_col': 'latest_post_id', 'type': 'Int', 'divisor': 1, 'suffix': '', 'width': 8,
         'text': 'Latest\nPost ID', 'widget': tk.Button()},
        {'db_col': 'latest_post_date', 'type': 'Date', 'suffix': '', 'width': 12,
         'text': 'Latest\nPost Date', 'widget': tk.Button()},
        {'db_col': 'last_seen_date', 'type': 'DateTime', 'suffix': '', 'width': 16,
         'text': 'Last Seen', 'widget': tk.Button()},
        {'db_col': 'snr', 'type': 'Int', 'divisor': 1, 'suffix': ' dB', 'width': 8,
         'text': 'SNR', 'widget': tk.Button()},
        {'db_col': 'capabilities', 'type': 'Text', 'suffix': '', 'width': 8,
         'text': 'Cap.', 'widget': tk.Button()},
        {'db_col': 'is_selected', 'db_type': 'Int', 'divisor': 1, 'suffix': '', 'width': 0,
         'text': None, 'widget': tk.Button()},
    ]

    def __init__(self, frame, f2b_q: queue.Queue, b2f_q: queue.Queue):

        self.f2b_q = f2b_q
        self.b2f_q = b2f_q

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
                    blog['widget'].grid(column=col, row=(row + 1))  # need to row+1 to allow for header

    def reload_blog_list(self):
        # clear all entries
        for row, _ in enumerate(self.blog_list):
            for col, blog in enumerate(self.blog_list[row]):
                blog['widget'].configure(state=tk.NORMAL)
                blog['widget'].delete(1.0, tk.END)

        blogs_table = DbTable('blogs')

        fields = []
        for field in self.blog_list_headers:
            fields.append(field['db_col'])

        db_values = blogs_table.select(order_by='last_seen_date', desc=True, limit=30,
                                       hdr_list=fields)

        for row, db_row in enumerate(db_values):
            for col, col_name in enumerate(list(db_row)):
                if col_name == 'is_selected':  # this marks the end of the list, and we don't add it to the grid
                    break

                if self.blog_list_headers[col]['type'] == 'Int':
                    number = int(int(db_row[col_name])/int(self.blog_list_headers[col]['divisor']))
                    value = locale.format_string("%d", number, grouping=True) + self.blog_list_headers[col]['suffix']

                elif self.blog_list_headers[col]['type'] == 'Float':
                    number = float(float(db_row[col_name])/float(self.blog_list_headers[col]['divisor']))
                    value = locale.format_string("%0.3f", number, grouping=True) + self.blog_list_headers[col]['suffix']

                elif self.blog_list_headers[col]['type'] == 'Date':
                    if int(db_row[col_name]) > 0:
                        value = time.strftime(
                            "%Y-%m-%d", time.gmtime(db_row[col_name])
                        ) + self.blog_list_headers[col]['suffix']
                    else:
                        value = 'unknown'

                elif self.blog_list_headers[col]['type'] == 'DateTime':
                    if int(db_row[col_name]) > 0:
                        value = time.strftime(
                            "%Y-%m-%d %H:%M", time.gmtime(db_row[col_name])
                        ) + self.blog_list_headers[col]['suffix']
                    else:
                        value = 'unknown'
                else:
                    value = db_row[col_name] + self.blog_list_headers[col]['suffix']

                blog_cell = self.blog_list[row][col]
                blog_cell['widget'].tag_configure('tag_all', justify='center')
                blog_cell['widget'].insert('1.0', value)
                blog_cell['widget'].tag_add('tag_all', '1.0', tk.END)
                blog_cell['widget'].tag_bind('tag_all', '<Button-1>',
                                             ft.partial(self.select_blog, row))
                if db_row['is_selected']:  # check the selected flag
                    blog_cell['widget'].configure(bg='#3498db')
                else:  # check the selected flag
                    blog_cell['widget'].configure(bg='#ffffff')
                blog_cell['widget'].configure(state=tk.DISABLED)

        return

    def get_value_by_row_db_col(self, row: int, db_col: str):
        for i, col in enumerate(self.blog_list_headers):
            if col['db_col'] == db_col:
                return self.blog_list[row][i]['widget'].get(1.0, tk.END).replace('\n', '')

        return None

    # noinspection PyGlobalUndefined
    def select_blog(self, row, event):
        req = GuiMessage()
        req.set_cmd('S')
        station = self.get_value_by_row_db_col(row, 'station')
        req.set_cli_input(f'@ {station} is now the selected blog')
        req.set_blog(self.get_value_by_row_db_col(row, 'blog'))
        req.set_station(station)
        freq_string = self.get_value_by_row_db_col(row, 'frequency')
        # annoyingly, we must convert a string in the form 14,078 MHz back into an integer
        freq_string = re.findall(r"([0-9]*)[.,]?([0-9]+) MHz", freq_string)
        freq = (int(freq_string[0][0]) * 1000000) + (int(freq_string[0][1]) * 1000)
        req.set_frequency(freq)
        req.set_ts()
        self.f2b_q.put(req)
        logging.logmsg(3, f"fe: {req}")


class GuiMain:

    def __init__(self, frame, f2b_q: queue.Queue, b2f_q: queue.Queue):
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

        self.latest_posts = GuiLatestPosts(frame_latest_list, f2b_q)

        # QSO Area follows - middle of main
        frame_qso = tk.Frame(frame_mid)
        frame_qso.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.qso_box = GuiQsoBox(frame_qso)

        frame_cli = tk.Frame(frame_mid)
        frame_cli.pack(side=tk.BOTTOM, padx=4)

        self.cli = GuiCli(frame_mid, f2b_q)

        # Blog list area - right of main
        frame_blog_list = tk.Frame(frame_right, bg='white', padx=4, pady=4)
        frame_blog_list.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.blog_list = GuiBlogList(frame_blog_list, f2b_q, b2f_q)

    def reload_latest(self):
        self.latest_posts.reload_latest()

    def reload_qso_box(self):
        self.qso_box.reload_qso_box()

    def reload_cli(self):
        self.cli.reload_cli()

    def reload_blog_list(self):
        self.blog_list.reload_blog_list()
