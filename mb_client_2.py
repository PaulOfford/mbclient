import tkinter as tk
from tkinter import ttk
import tkinter.font as font
import time

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


class GuiMain:

    latest_text = []

    def __init__(self, main_frame):
        pane_main = tk.PanedWindow(main_frame, bg='#606060', height=200)
        pane_main.pack(fill='both', expand=1, side='top')

        frame_left = tk.Frame(pane_main, bg='white', width=300)
        pane_main.add(frame_left)

        frame_mid = tk.Frame(pane_main, bg='light green', width=420, padx=4)
        pane_main.add(frame_mid)

        frame_right = tk.Frame(pane_main, bg='blue', width=300, padx=4)
        pane_main.add(frame_right)

        frame_latest_list = tk.Frame(frame_left, bg='white')
        frame_latest_list.pack()

        latest_list_hdr = tk.Label(
            frame_latest_list,
            text="Latest Posts",
            bg='white',
            font=font_main_ul,
            justify=tk.LEFT,
            anchor=tk.W,
            padx=4
        )
        latest_list_hdr.pack(anchor='ne', fill=tk.X)

        self.latest_text.append(tk.StringVar())
        latest_01_btn = tk.Button(
            frame_latest_list,
            textvariable=self.latest_text[len(self.latest_text) - 1],
            font=font_main,
            activebackground='#f0f0f0',
            bg='white', height=1, width=50,
            anchor=tk.W,
            padx=4,
            pady=3,
            relief='flat'
        )
        latest_01_btn.pack(anchor='ne', fill=tk.X)

        self.latest_text.append(tk.StringVar())
        latest_02_btn = tk.Button(
            frame_latest_list,
            textvariable=self.latest_text[len(self.latest_text) - 1],
            font=font_main,
            activebackground='#f0f0f0',
            bg='white', height=1, width=50,
            anchor=tk.W,
            padx=4,
            pady=3,
            relief='flat'
        )
        latest_02_btn.pack(anchor='ne', fill=tk.X)


frame_container = tk.Frame(root)
frame_container.pack(fill='x', expand=1, side='top', anchor='n')

frame_hdr = tk.Frame(frame_container, background="black", height=100, pady=10)
frame_hdr.pack(fill='x', expand=1, side='top', anchor='n')
header = GuiHeader(header_frame=frame_hdr)  # populate the header

frame_main = tk.Frame(frame_container, pady=4)
frame_main.pack(fill='both', expand=1, side='top', anchor='n')
main = GuiMain(main_frame=frame_main)  # populate the main area

# Now for the logic

header.set_frequency('14.078 000')
header.set_offset('1800 Hz')
header.set_callsign('2E0FGO')
header.clock_tick()

main.latest_text[0].set("2023-02-07 11:04 - EmComms Due to Earthquake in Turkey")
main.latest_text[1].set("2023-02-03 08:30 - K7RA Solar Update")

root.mainloop()
