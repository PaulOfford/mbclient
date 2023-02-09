import tkinter as tk
from tkinter import ttk
import tkinter.font as font
import time

max_post_list = 30
max_qsos = 4

root = tk.Tk()
root.title("Microblog Client r1")
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
    to_value = 0

    def __init__(self, to_in_secs: int):
        self.to_value = to_in_secs

    # ToDo: Finish this class


class ScrollableFrame(ttk.Frame):
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
                    height=1, width=50,
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


class GuiQsoBox:

    qso_text = []
    qso_label = []

    def __init__(self, frame):
        # ok - I'm not proud of this, but I have tried everything I can think of to get the scrollable
        # frame to expand
        junk_text = "\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t"
        junk = tk.Label(
            frame.scrollable_frame,
            text=junk_text,
            bg='#ffeaa7',
            font=font_main,
            justify=tk.LEFT,
            anchor=tk.W,
            padx=4,
            pady=3,
        )
        junk.pack(fill=tk.X, expand=1, anchor='ne')

        global max_qsos
        for i in range(0, max_qsos):
            self.qso_text.append(tk.StringVar())

        for index in range(0, max_qsos):
            self.qso_label.append(
                tk.Label(
                    frame.scrollable_frame,
                    textvariable=self.qso_text[index],
                    font=font_main,
                    bg='#ffeaa7',
                    anchor=tk.W,
                    justify=tk.LEFT,
                    wraplength=360,
                    padx=10,
                    pady=3, relief='flat'
                )
            )
            self.qso_label[-1].pack(anchor='ne', fill=tk.X)

    def append_qso(self, value: str):
        list_length = len(self.qso_text)
        for index in range(list_length - 1, 0, -1):  # index starts by addressing the last entry
            self.qso_text[index - 1].set(self.qso_text[index].get())
        self.qso_text[list_length - 1].set(value)


class GuiCli:

    cli_hdr_text = tk.StringVar()

    def __init__(self, frame):

        cli_hdr = tk.Label(frame,
                           textvariable=self.cli_hdr_text,
                           bg='#6699ff',
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


class GuiMain:

    latest_posts = None

    def __init__(self, main_frame):
        pane_main = tk.PanedWindow(main_frame, bg='#606060')
        pane_main.pack(fill='both', expand=1, side='top')

        frame_left = tk.Frame(pane_main)
        pane_main.add(frame_left)

        frame_mid = tk.Frame(pane_main)
        pane_main.add(frame_mid, width=480)

        frame_right = tk.Frame(pane_main, bg='blue')
        pane_main.add(frame_right)

        # Latest Posts area
        frame_latest_list = tk.Frame(frame_left, bg='white')
        frame_latest_list.pack()

        self.latest_posts = GuiLatestPosts(frame_latest_list)

        # QSO Area follows - middle of main
        frame_qso_outer = tk.Frame(frame_mid, width=480)
        frame_qso_outer.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        frame_qso = ScrollableFrame(frame_qso_outer)
        frame_qso.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=4)

        self.qso_box = GuiQsoBox(frame_qso)

        frame_cli = tk.Frame(frame_mid)
        frame_cli.pack(side=tk.BOTTOM, padx=4)

        self.cli = GuiCli(frame_mid)

        # Blog list area - right of main

    def prepend_latest(self, value: str):
        self.latest_posts.prepend_latest(value)

    def append_qso(self, value: str):
        self.qso_box.append_qso(value)

    def set_selected_blog(self, blog: str):
        self.cli.set_selected_blog(blog)


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

main = GuiMain(main_frame=frame_main)  # populate the main area

main.prepend_latest("2023-02-03 08:30 - K7RA Solar Update")
main.prepend_latest("2023-02-07 11:04 - EmComms Due to Earthquake in Turkey")

main.append_qso(
    "18:07:28 - (1800) - M0PXO: 2E0FGO  +M.L >0\n"
    "20 - MARINES TO GAIN RADIO OP EXPERIENCE\n"
    "21 - MORE HAMS ON THE ISS\n"
    "22 - HAARP THANKS HAMS\n"
    "23 - K7RA SOLAR UPDATE\n"
    "24 - RSGB PROPOGATION NEWS\n"
)

main.append_qso(
    "18:10:02 - (1800) - M0PXO: 2E0FGO  +GE 24\n"
    "PROPAGATION NEWS - 15 JANUARY 2023\n\n"
    "SUNSPOT REGION 3186 HAS ROTATED INTO VIEW OFF THE SUN'S NORTHEAST LIMB AND PRODUCE"
    " AN X1.0 SOLAR FLARE AT 2247UTC ON THE 10 JANUARY. IT MAY HAVE THROWN SOME PLASMA INTO"
    " SPACE IN THE FORM OF A CORONAL MASS EJECTION BUT, AS IT IS NOT YET DIRECTLY FACING EARTH,"
    " THE CME IS LIKELY DIRECTED AWAY FROM US.\n\n"
    "WE CURRENTLY HAVE AN SFI IN THE 190S."
)

main.append_qso(
    "14:25:48 - (1800) - M0PXO: 2E0FGO  +M.L >2023-01-17\n"
    "25 - FALCONSAT-3 NEARS REENTRY\n"
    "26 - 2026 WORLD RADIOSPORT TEAM CHAMPIONSHIP NEWS\n"
    "27 - RSGB PROPOGATION NEWS\n"
    "28 - YAESU RADIOS DONATED TO ARRL\n"
    "29 - RSGB PROPOGATION NEWS\n"
)

main.append_qso(
    "14:28:47 - (1800) - M0PXO: 2E0FGO  +M.G 25\n"
    "AMATEUR SATELLITE FALCONSAT-3 NEARS REENTRY\n\n"
    "2023-01-20\n"
    "FS-3 IS PREDICTED TO REENTER THE EARTHS ATMOSPHERE IN THE WEEK OF JANUARY 16 - 21, 2023."
    "  RADIO AMATEUR SATELLITE CORPORATION (AMSAT) BOARD MEMBER AND FS-3 CONTROL OPERATOR, MARK HAMMOND,"
    " N8MH, SAID HE WILL TRY TO HAVE THE SATELLITE OPERATIONAL FOR ITS FINAL HOURS.\n\n"
    "THE SATELLITE HAS ONLY BEEN AVAILABLE FOR APPROXIMATELY 24 HOURS EACH WEEKEND DUE TO WEAK BATTERIES.\n"
)

main.set_selected_blog('M0PXO')

root.mainloop()
