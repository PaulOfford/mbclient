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
        ('max_blogs', 'Max Blogs:', 'entry', tk.IntVar(sw)),
        ('max_posts', 'Max Posts:', 'entry', tk.IntVar(sw)),
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


class GuiTable:

    table_data = None  # this is a list of entries, each of which is a dictionary
    table_headers = None
    select_cb = None

    def get_cell_string(self, col: int, db_data) -> str:
        if self.table_headers[col]['type'] == 'Int':
            number = int(int(db_data) / int(self.table_headers[col]['divisor']))
            value = locale.format_string("%d", number, grouping=True) + self.table_headers[col]['suffix']

        elif self.table_headers[col]['type'] == 'Float':
            number = float(float(db_data) / float(self.table_headers[col]['divisor']))
            value = locale.format_string("%0.3f", number, grouping=True) + self.table_headers[col]['suffix']

        elif self.table_headers[col]['type'] == 'Date':
            if int(db_data) > 0:
                value = time.strftime(
                    "%Y-%m-%d", time.gmtime(db_data)
                ) + self.table_headers[col]['suffix']
            else:
                value = 'unknown'

        elif self.table_headers[col]['type'] == 'DateTime':
            if int(db_data) > 0:
                value = time.strftime(
                    "%Y-%m-%d %H:%M", time.gmtime(db_data)
                ) + self.table_headers[col]['suffix']
            else:
                value = 'unknown'
        else:
            value = db_data + self.table_headers[col]['suffix']

        return value

    def __init__(self, frame, column_defs, max_rows: int, select_method, hdr_click_method):
        self.table_headers = column_defs
        self.select_cb = select_method
        self.hdr_click_cb = hdr_click_method

        # construct the table
        self.table_data = [[{} for _, _ in enumerate(self.table_headers)] for _ in range(max_rows + 1)]

        # initialise the table
        for row, _ in enumerate(self.table_data):
            for col, row_data in enumerate(self.table_data[row]):
                row_data['db_col'] = self.table_headers[col]['db_col']
                row_data['tv'] = None
                row_data['widget'] = tk.Text()
                row_data['selected'] = tk.FALSE

        # set the blog list columns to equal weight
        frame.grid(columnspan=len(self.table_headers))
        for i, _ in enumerate(self.table_headers):
            frame.columnconfigure(i, weight=1)

        # set the blog list headers
        for col, headers in enumerate(self.table_headers):
            if headers['label']:
                headers['widget'] = tk.Text(
                    frame,
                    bg='white',
                    font=font_main_bold,
                    relief=tk.FLAT,
                    width=self.table_headers[col]['width'],
                    height=1,
                    padx=10
                )
                headers['widget'].grid(row=0, column=col)
                headers['widget'].tag_configure('tag_all', justify=self.table_headers[col]['justify'])
                headers['widget'].insert('1.0', self.table_headers[col]['label'])
                headers['widget'].tag_add('tag_all', '1.0', tk.END)
                headers['widget'].tag_bind(
                    'tag_all', '<Button-1>', ft.partial(self.hdr_click_cb, col)
                )

                headers['widget'].configure(state=tk.DISABLED)

        # add the blog list Text widgets to the grid
        for row, _ in enumerate(self.table_data):
            for col, blog in enumerate(self.table_data[row]):
                if self.table_headers[col]['label']:
                    blog['widget'] = tk.Text(
                        frame,
                        bg='white',
                        font=font_main,
                        relief=tk.FLAT,
                        width=self.table_headers[col]['width'],
                        height=1,
                        padx=10
                    )
                    blog['widget'].grid(column=col, row=(row + 1))  # need to row+1 to allow for header

    def reload_table(self, db_values):
        # clear all entries
        for row, _ in enumerate(self.table_data):
            for col, row_data in enumerate(self.table_data[row]):
                row_data['widget'].configure(state=tk.NORMAL)
                row_data['widget'].configure(bg='#ffffff')
                row_data['widget'].delete(1.0, tk.END)

        fields = []
        for field in self.table_headers:
            fields.append(field['db_col'])

        for row, db_row in enumerate(db_values):
            for col, col_name in enumerate(list(db_row)):
                if col_name == 'is_selected':  # this marks the end of the list, and we don't add it to the grid
                    break

                value = self.get_cell_string(col, db_row[col_name])
                cell = self.table_data[row][col]
                cell['widget'].tag_configure('tag_all', justify=self.table_headers[col]['justify'])
                cell['widget'].insert('1.0', value)
                cell['widget'].tag_add('tag_all', '1.0', tk.END)
                cell['widget'].tag_bind(
                    'tag_all', '<Button-1>', ft.partial(self.select_cb, row)
                )
                cell['widget'].tag_bind(
                    'tag_all', '<Button-3>', ft.partial(self.popup_cb, row)
                )
                if db_row['is_selected']:  # check the selected flag
                    cell['widget'].configure(bg='#6699FF')
                else:  # check the selected flag
                    cell['widget'].configure(bg='#ffffff')
                cell['widget'].configure(state=tk.DISABLED)

        return


class GuiBlogList(GuiTable):
    blog_list_headers = [
        {'db_col': 'blog', 'type': 'Text', 'suffix': '', 'width': 10,
         'label': 'Blog', 'widget': tk.Button(), 'justify': 'left'},
        {'db_col': 'station', 'type': 'Text', 'suffix': '', 'width': 0,
         'label': '', 'widget': tk.Button(), 'justify': 'left'},
        {'db_col': 'frequency', 'type': 'Float', 'divisor': 1000000, 'suffix': '', 'width': 8,
         'label': 'Freq\nMHz', 'widget': tk.Button(), 'justify': 'center'},
        {'db_col': 'latest_post_id', 'type': 'Int', 'divisor': 1, 'suffix': '', 'width': 6,
         'label': 'Latest', 'widget': tk.Button(), 'justify': 'center'},
        {'db_col': 'latest_post_date', 'type': 'Date', 'suffix': '', 'width': 10,
         'label': 'Date', 'widget': tk.Button(), 'justify': 'center'},
        {'db_col': 'last_seen_date', 'type': 'DateTime', 'suffix': '', 'width': 15,
         'label': 'Last Seen', 'widget': tk.Button(), 'justify': 'center'},
        {'db_col': 'is_selected', 'db_type': 'Int', 'divisor': 1, 'suffix': '', 'width': 0,
         'label': None, 'widget': tk.Button(), 'justify': 'center'},
    ]

    db_values = None  # data returned from the blog table query
    blog_list_pop_up = None  # pop up widget
    clicked_row = None  # holds the db_values row number that has been right clicked

    def __init__(self, frame, f2b_q: queue.Queue, b2f_q: queue.Queue):
        # ToDo: this frame needs horizontal and vertical scroll bars
        self.f2b_q = f2b_q
        self.b2f_q = b2f_q
        super().__init__(
            frame, self.blog_list_headers, settings.max_blogs, self.cb_row_select, self.cb_hdr_click
        )
        # set up the pop up menu
        self.blog_list_pop_up = tk.Menu(frame, tearoff=False)
        self.blog_list_pop_up.add_command(label='Get recent', command=self.list_recent)
        self.blog_list_pop_up.add_command(label='Refresh', command=self.check_for_latest)

    # list_recent causes MbClient to update the Post List with the five most recent posts
    def list_recent(self):
        req = GuiMessage()
        req.set_cmd('E')
        req.set_blog(self.db_values[self.clicked_row]['blog'])
        req.set_station(self.db_values[self.clicked_row]['station'])
        req.set_frequency(self.db_values[self.clicked_row]['frequency'])
        req.set_op('recent')
        req.set_ts()
        self.f2b_q.put(req)
        logging.logmsg(3, f"fe: {req}")

    # check_for_latest causes MbClient to request an @MB announcement
    def check_for_latest(self):
        req = GuiMessage()
        req.set_cmd('Q')
        req.set_blog(self.db_values[self.clicked_row]['blog'])
        req.set_station(self.db_values[self.clicked_row]['station'])
        req.set_frequency(self.db_values[self.clicked_row]['frequency'])
        req.set_op('latest')
        req.set_ts()
        self.f2b_q.put(req)
        logging.logmsg(3, f"fe: {req}")

    def reload_blog_list(self):
        blogs_table = DbTable('blogs')

        fields = []
        for field in self.blog_list_headers:
            fields.append(field['db_col'])

        self.db_values = blogs_table.select(
            order_by='last_seen_date', desc=True, limit=settings.max_blogs, hdr_list=fields
        )

        self.reload_table(self.db_values)

        return

    # noinspection PyGlobalUndefined
    def cb_row_select(self, row, event):
        req = GuiMessage()
        req.set_cmd('S')
        req.set_blog(self.db_values[row]['blog'])
        req.set_station(self.db_values[row]['blog'])
        req.set_frequency(self.db_values[row]['frequency'])
        req.set_ts()
        self.f2b_q.put(req)
        logging.logmsg(3, f"fe: {req}")

    def popup_cb(self, row, event):
        self.clicked_row = row
        self.blog_list_pop_up.tk_popup(event.x_root, event.y_root)

    def cb_hdr_click(self, col, event):
        pass


class GuiPostListBox(GuiTable):

    post_list_headers = [
        {'db_col': 'post_id', 'type': 'Int', 'divisor': 1, 'suffix': '', 'width': 6,
         'label': 'ID', 'widget': tk.Button(), 'justify': 'center'},
        {'db_col': 'post_date', 'type': 'Date', 'suffix': '', 'width': 10,
         'label': 'Date', 'widget': tk.Button(), 'justify': 'center'},
        {'db_col': 'title', 'type': 'Text', 'suffix': '', 'width': 128,
         'label': 'Subject', 'widget': tk.Button(), 'justify': 'left'},
        {'db_col': 'is_selected', 'db_type': 'Int', 'divisor': 1, 'suffix': '', 'width': 0,
         'label': None, 'widget': tk.Button(), 'justify': 'center'},
    ]

    db_values = None  # data returned from the blog table query
    post_list_pop_up = None

    def __init__(self, frame: tk.Frame, f2b_q: queue.Queue, b2f_q: queue.Queue):
        # ToDo: this frame needs horizontal and vertical scroll bars
        self.f2b_q = f2b_q
        self.b2f_q = b2f_q

        super().__init__(
            frame, self.post_list_headers, settings.max_posts, self.cb_row_select, self.cb_hdr_click
        )
        # set up the pop up menu
        self.post_list_pop_up = tk.Menu(frame, tearoff=False)
        self.post_list_pop_up.add_command(label='Refresh listing', command=self.refresh_listing)
        self.post_list_pop_up.add_command(label='Refresh content', command=self.refresh_content)

    def reload_post_list(self):
        status = Status()

        post_table = DbTable('post')

        fields = []
        for field in self.post_list_headers:
            fields.append(field['db_col'])

        self.db_values = post_table.select(
            where=f"blog='{status.selected_blog}'",
            order_by='post_id', desc=True,
            limit=settings.max_posts,
            hdr_list=fields
        )

        self.reload_table(self.db_values)

        return

    def popup_cb(self, row, event):
        self.post_list_pop_up.tk_popup(event.x_root, event.y_root)

    def cb_row_select(self, row, event):
        status = Status()

        req = GuiMessage()
        req.set_cmd('F')
        req.set_blog(status.selected_blog)
        req.set_post_id(self.db_values[row]['post_id'])
        req.set_ts()
        self.f2b_q.put(req)
        logging.logmsg(3, f"fe: {req}")

    def refresh_listing(self, row, event):
        req = GuiMessage()
        req.set_cmd('E')
        req.set_blog(self.db_values[row]['blog'])
        req.set_post_id(self.db_values[row]['post_id'])
        req.set_ts()
        self.f2b_q.put(req)
        logging.logmsg(3, f"fe: {req}")

    def refresh_content(self, row, event):
        req = GuiMessage()
        req.set_cmd('G')
        req.set_blog(self.db_values[row]['blog'])
        req.set_post_id(self.db_values[row]['post_id'])
        req.set_ts()
        self.f2b_q.put(req)
        logging.logmsg(3, f"fe: {req}")

    def cb_hdr_click(self, col, event):
        pass


class GuiPostContent:

    f2b_q = None
    post_box = None
    post_cols = ['qso_date', 'post_id', 'post_date', 'title', 'body', 'is_selected']

    def __init__(self, frame: tk.Frame, f2b_q: queue.Queue):
        self.f2b_q = f2b_q

        post_content_hdr = tk.Label(
            frame,
            text="Post",
            bg='white',
            font=font_main_ul,
            justify=tk.LEFT,
            anchor=tk.W,
            padx=10, pady=12
        )
        post_content_hdr.pack(anchor='ne', fill=tk.X)

        self.post_box = tk.Text(
            frame, width=300, wrap=tk.WORD, padx=10, pady=5,
            font=font_main, bg='#ffffff',
            spacing1=1.1, spacing2=1.1,
            borderwidth=0
        )
        self.post_box.pack(fill=tk.BOTH, expand=1, anchor='ne')

        self.reload_post_content()

    def get_post(self, blog: str, frequency: int, post_id: int):

        req = GuiMessage()

        req.set_blog(blog)
        req.set_frequency(frequency)
        req.set_cli_input(f'G {post_id}')
        req.set_cmd('G')
        req.set_op('eq')
        req.set_post_id(post_id)
        req.set_post_date(0)
        req.set_ts()
        self.f2b_q.put(req)
        logging.logmsg(3, f"fe: {req}")

    def get_post_cb(self, event):
        status = Status()
        self.get_post(status.selected_blog, status.radio_frequency, status.selected_post)

    def reload_post_content(self):
        status = Status()
        post_string = f"{status.selected_post}"

        qso_table = DbTable('post')
        db_values = qso_table.select_latest(
            where=f"blog='{status.selected_blog}' AND post_id={status.selected_post}",
            order_by='post_id',
            limit=1,
            hdr_list=self.post_cols
        )

        self.post_box.configure(state=tk.NORMAL)
        self.post_box.delete(1.0, 'end')

        if len(db_values) > 0:
            for i, r in enumerate(db_values):
                if r['post_date'] > 0:
                    p_date = time.strftime("%Y-%m-%d", time.gmtime(r['post_date']))
                    post_string += f" {p_date}"

                if len(r['title']):
                    post_string += f" {r['title']}"

                if len(r['body']):
                    post_string += f"\n\n{r['body']}\n"
                else:
                    # we need to ask the operator if we should get the post from the server
                    post_string += f"\n\nWe don't have the content for this post in the cache. "
                    post_string += f"Click here to get it from the server."

                self.post_box.insert(tk.END, post_string)

                # we need to add a hotlink to allow the operator to get the missing content
                self.post_box.tag_add('get_post_link', '1.0', tk.END)
                self.post_box.tag_bind(
                    'get_post_link', '<Button-1>',
                    ft.partial(self.get_post_cb)
                )

                self.post_box.see(tk.END)

        self.post_box.configure(state=tk.DISABLED)

        return


class GuiMain:

    def __init__(self, frame, f2b_q: queue.Queue, b2f_q: queue.Queue):
        pane_main = tk.PanedWindow(frame, bg='#606060')
        pane_main.pack(fill='both', expand=1, side='top')

        frame_left = tk.Frame(pane_main, bg='white')
        pane_main.add(frame_left, width=480)

        frame_mid = tk.Frame(pane_main, bg='white')
        pane_main.add(frame_mid, width=520)

        frame_right = tk.Frame(pane_main, bg='white')
        pane_main.add(frame_right, width=160)

        # Blog list area - right of main
        frame_blog_list = tk.Frame(frame_left, bg='white', padx=4, pady=4, width=1.0)
        frame_blog_list.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.blog_list = GuiBlogList(frame_blog_list, f2b_q, b2f_q)

        # Post List Area follows - middle of main
        frame_post_list = tk.Frame(frame_mid)
        frame_post_list.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.post_list = GuiPostListBox(frame_post_list, f2b_q, b2f_q)

        # Latest Posts area
        frame_latest_list = tk.Frame(frame_right, bg='white')
        frame_latest_list.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.post_content = GuiPostContent(frame_latest_list, f2b_q)

    def reload_post_content(self):
        self.post_content.reload_post_content()

    def reload_post_list_box(self):
        self.post_list.reload_post_list()

    def reload_blog_list(self):
        self.blog_list.reload_blog_list()
