import tkinter as tk
from tkinter import ttk
import tkinter.font as font
import time

# I'm just developing ideas here -> this code is very messy

class FrequencyControl:

    js8_freqs = [
        1.842,
        3.578,
        7.078,
        10.130,
        14.078,
        18.104,
        21.078,
        24.922,
        27.245,
        28.078,
        50.318,
    ]

    is_scanning = False

    def toggle_scan(self):
        global scan_btn
        if self.is_scanning:
            self.is_scanning = False
            scan_btn.configure(bg='#22ff23')
        else:
            self.is_scanning = True
            scan_btn.configure(bg='#ff2222')

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

def tick(curtime=''):  # used for the header clock
    newtime = time.strftime('%Y-%m-%d %H:%M:%S')
    if newtime != curtime:
        curtime = newtime
        clockLabel.config(text=curtime)
    clockLabel.after(200, tick, curtime)


freq_ctrl = FrequencyControl()

root = tk.Tk()
root.title("Microblog Client r1")

font_btn = font.Font(family='Ariel', size=9, weight='normal')
font_btn_bold = font.Font(family='Ariel', size=9, weight='bold')
font_hdr = font.Font(family='Ariel', size=14, weight='normal')
font_freq = font.Font(family='Seven Segment', size=24, weight='normal')
font_main = font.Font(family='Ariel', size=8, weight='normal')
font_main_ul = font.Font(family='Ariel', size=8, weight='normal', underline=True)
font_main_hdr = font.Font(family='Ariel', size=10, weight='normal')
font_main_bold = font.Font(family='Ariel', size=8, weight='bold')

# root.geometry("1080x720")

# ---------------------------------------------------------------------------------------
# HEADER AREA
# ---------------------------------------------------------------------------------------

frame_hdr = tk.Frame(root, background="black", height=100, pady=17)
frame_hdr.grid(columnspan=3, rowspan=2)
frame_hdr.columnconfigure(0, weight=1, minsize=280)
frame_hdr.columnconfigure(1, weight=1, minsize=480)
frame_hdr.columnconfigure(2, weight=1, minsize=320)

# frequency in the header
freq_text = tk.StringVar()
hdr_freq = tk.Label(frame_hdr, textvariable=freq_text,
                    bg='black', fg='white',
                    font=font_freq
                    )
hdr_freq.grid(column=0, row=0, padx=10)
freq_text.set('14.078 000')

offset_text = tk.StringVar()
hdr_offset = tk.Label(
    frame_hdr, textvariable=offset_text,
    bg='black', fg='white',
    font=font_hdr,
    justify=tk.LEFT
)
hdr_offset.grid(column=0, row=1, padx=10)
offset_text.set('1800 Hz')

# Callsign
callsign_text = tk.StringVar()
hdr_callsign = tk.Label(frame_hdr, textvariable=callsign_text,
                        bg='black', fg='white',
                        font=font_hdr,
                        )
hdr_callsign.grid(column=1, row=0, sticky=tk.EW)
callsign_text.set('2E0FGO')  # very ugly - try to improve

clockLabel = tk.Label(frame_hdr,
                      bg='black', fg='white',
                      font=font_hdr,
                      anchor=tk.E
                      )
clockLabel.grid(column=1, row=1)

# Scan button
scan_text = tk.StringVar()
scan_btn = tk.Button(
    frame_hdr, textvariable=scan_text,
    font=font_btn_bold,
    bg='#22ff23', height=1, width=18,
    pady=3, relief='flat',
    command=freq_ctrl.toggle_scan
)
scan_btn.grid(column=2, row=0)
scan_text.set('Scan')


# ---------------------------------------------------------------------------------------
# MAIN AREA - contains the activity list, qso details and available mb servers
# ---------------------------------------------------------------------------------------

frame_main = tk.Frame(root, pady=17)
frame_main.grid(columnspan=3, rowspan=1)
frame_main.columnconfigure(0, weight=1, minsize=280)
frame_main.columnconfigure(1, weight=1, minsize=444)
frame_main.columnconfigure(2, weight=1, minsize=320)

frame_conv_list = tk.Frame(frame_main, bg='white', padx=2)
frame_conv_list.grid(column=0, row=0, sticky='news')

conv_list_hdr = tk.Label(
    frame_conv_list,
    text="Server: Client Message",
    bg='white',
    font=font_main,
    justify=tk.LEFT,
    anchor=tk.W
)
conv_list_hdr.grid(column=0, row=0, padx=2, sticky=tk.EW)

conv_01_text = tk.StringVar()
conv_01_btn = tk.Button(frame_conv_list,
                        textvariable=conv_01_text,
                        font=font_main,
                        activebackground='#f0f0f0',
                        bg='white', height=1, width=50,
                        anchor=tk.W,
                        pady=3, relief='flat'
                        )
conv_01_btn.grid(column=0, row=1, padx=2, sticky=tk.W)
conv_01_text.set("M0PXO: 2E0FGO -M.L 55 POST NOT FOUND")

frame_qso_outer = tk.Frame(frame_main)
frame_qso_outer.grid(column=1, row=0, sticky='news')

frame_qso = ScrollableFrame(frame_qso_outer)
frame_qso.pack(side=tk.TOP, fill=tk.BOTH, expand=1, padx=4)


qso_01_text = tk.StringVar()
qso_01 = tk.Label(
    frame_qso.scrollable_frame,
    textvariable=qso_01_text,
    font=font_main,
    bg='#ffeaa7',
    anchor=tk.W,
    justify=tk.LEFT,
    wraplength=400,
    padx=10,
    pady=3, relief='flat'
)
qso_01.pack(fill='both', expand=1)
qso_01_text.set(
    "18:07:28 - (1800) - M0PXO: 2E0FGO  +M.L >0\n"
    "20 - MARINES TO GAIN RADIO OP EXPERIENCE\n"
    "21 - MORE HAMS ON THE ISS\n"
    "22 - HAARP THANKS HAMS\n"
    "23 - K7RA SOLAR UPDATE\n"
    "24 - RSGB PROPOGATION NEWS\n"
)


qso_02_text = tk.StringVar()
qso_02 = tk.Label(
    frame_qso.scrollable_frame,
    textvariable=qso_02_text,
    font=font_main,
    bg='#ffeaa7',
    anchor=tk.W,
    justify=tk.LEFT,
    wraplength=400,
    padx=10,
    pady=3, relief='flat'
)
qso_02.pack(fill=tk.X)
qso_02_text.set(
    "18:10:02 - (1800) - M0PXO: 2E0FGO  +GE 24\n"
    "PROPAGATION NEWS - 15 JANUARY 2023\n\n"
    "SUNSPOT REGION 3186 HAS ROTATED INTO VIEW OFF THE SUN'S NORTHEAST LIMB AND PRODUCE"
    " AN X1.0 SOLAR FLARE AT 2247UTC ON THE 10 JANUARY. IT MAY HAVE THROWN SOME PLASMA INTO"
    " SPACE IN THE FORM OF A CORONAL MASS EJECTION BUT, AS IT IS NOT YET DIRECTLY FACING EARTH,"
    " THE CME IS LIKELY DIRECTED AWAY FROM US.\n\n"
    "WE CURRENTLY HAVE AN SFI IN THE 190S."
)

qso_03_text = tk.StringVar()
qso_03 = tk.Label(
    frame_qso.scrollable_frame,
    textvariable=qso_03_text,
    font=font_main,
    bg='#ffeaa7',
    anchor=tk.W,
    justify=tk.LEFT,
    wraplength=400,
    padx=10,
    pady=3, relief='flat'
)
qso_03.pack(fill=tk.X)
qso_03_text.set(
    "14:25:48 - (1800) - M0PXO: 2E0FGO  +M.L >2023-01-17\n"
    "25 - FALCONSAT-3 NEARS REENTRY\n"
    "26 - 2026 WORLD RADIOSPORT TEAM CHAMPIONSHIP NEWS\n"
    "27 - RSGB PROPOGATION NEWS\n"
    "28 - YAESU RADIOS DONATED TO ARRL\n"
    "29 - RSGB PROPOGATION NEWS\n"
)

qso_04_text = tk.StringVar()
qso_04 = tk.Label(
    frame_qso.scrollable_frame,
    textvariable=qso_04_text,
    font=font_main,
    bg='#ffeaa7',
    anchor=tk.W,
    justify=tk.LEFT,
    wraplength=400,
    padx=10,
    pady=3, relief='flat'
)
qso_04.pack(fill=tk.X)
qso_04_text.set(
    "14:28:47 - (1800) - M0PXO: 2E0FGO  +M.G 25\n"
    "AMATEUR SATELLITE FALCONSAT-3 NEARS REENTRY\n\n"
    "2023-01-20\n"
    "FS-3 IS PREDICTED TO REENTER THE EARTHS ATMOSPHERE IN THE WEEK OF JANUARY 16 - 21, 2023."
    "  RADIO AMATEUR SATELLITE CORPORATION (AMSAT) BOARD MEMBER AND FS-3 CONTROL OPERATOR, MARK HAMMOND,"
    " N8MH, SAID HE WILL TRY TO HAVE THE SATELLITE OPERATIONAL FOR ITS FINAL HOURS.\n\n"
    "THE SATELLITE HAS ONLY BEEN AVAILABLE FOR APPROXIMATELY 24 HOURS EACH WEEKEND DUE TO WEAK BATTERIES.\n"
)

qso_hdr_text = tk.StringVar()
qso_hdr = tk.Label(frame_qso_outer,
                   textvariable=qso_hdr_text,
                   bg='#6699ff',
                   font=font_main,
                   justify=tk.LEFT,
                   anchor=tk.W,
                   padx=4,
                   pady=3,
                   )
qso_hdr.pack(fill=tk.X, anchor=tk.W, padx=4, pady=4)
qso_hdr_text.set("Selected Blog: M0PXO")

cli_text = tk.Text(
    frame_qso_outer,
    font=font_main,
    width=50,
    height=1,
    padx=4,
    pady=4
)
cli_text.pack(fill=tk.X, padx=4, pady=4)

blog_list = [
    ["Mblog", "Station", "SNR", "Cap.", "Last Post", "Last Post"],
    ["AUSNEWS", "VK3WXY", "-25 dB", "LEGU", "2023-02-07", "405"],
    ["M0PXO", "M0PXO", "+01 dB", "LEG", "2023-02-03", "29"],
    ["NEWSEN", "K7GHI", "-24 dB", "LEG", "2023-01-31", "36"],
    ["NEWSEN", "K7MNO", "-13 dB", "LEG", "2023-01-30", "35"],
    ["NEWSSP", "K7MNO", "-14 dB", "LEG", "2023-01-27", "14"],
]

cell_str_array = [
    [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()],
    [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()],
    [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()],
    [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()],
    [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()],
    [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()],
]

blog_details = [
    [tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label()],
    [tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label()],
    [tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label()],
    [tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label()],
    [tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label()],
    [tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label(), tk.Label()],
]

frame_blog_list = tk.Frame(frame_main, bg='white', height=300, width=320, padx=2)
frame_blog_list.grid(column=2, row=0, sticky='news')

frame_blog_list.grid(columnspan=5)
frame_blog_list.columnconfigure(0, weight=1)
frame_blog_list.columnconfigure(1, weight=1)
frame_blog_list.columnconfigure(2, weight=1)
frame_blog_list.columnconfigure(3, weight=1)
frame_blog_list.columnconfigure(4, weight=1)
frame_blog_list.columnconfigure(5, weight=1)

row = 0
for blog in blog_list:
    for col in range(0, 5):
        if row == 0:
            blog_details[row][col] = tk.Label(
                frame_blog_list,
                textvariable=cell_str_array[row][col],
                bg='white',
                font=font_main_ul,
                justify=tk.LEFT,
                anchor=tk.W
            )
            blog_details[row][col].grid(column=col, row=row)
            new_str = blog_list[row][col]
            cell_str_array[row][col].set(value=new_str)
        else:
            blog_details[row][col] = tk.Label(
                frame_blog_list,
                textvariable=cell_str_array[row][col],
                bg='white',
                font=font_main,
                justify=tk.LEFT,
                anchor=tk.W
            )
            blog_details[row][col].grid(column=col, row=row)
            new_str = blog_list[row][col]
            cell_str_array[row][col].set(value=new_str)

    row = row + 1


tick()  # run the clock
root.mainloop()
