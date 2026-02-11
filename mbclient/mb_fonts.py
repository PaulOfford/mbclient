import tkinter.font as font
from tkinter import ttk
from .settings import user_settings


class MbFonts:
    font_btn = None
    font_btn_bold = None
    font_hdr = None
    font_freq = None
    font_main = None
    font_main_ul = None
    font_main_hdr = None
    font_main_bold = None
    font_console = None

    def __init__(self, base_font_size):
        self.font_btn = font.Font(family='Ariel', size=int(base_font_size * 1.125), weight='normal')
        self.font_btn_bold = font.Font(family='Ariel', size=int(base_font_size * 1.125), weight='bold')
        self.font_hdr = font.Font(family='Ariel', size=int(base_font_size * 1.75), weight='normal')
        # self.font_freq = font.Font(family='Seven Segment', size=int(base_font_size * 3), weight='normal')
        self.font_freq = font.Font(family='Ariel', size=int(base_font_size * 3), weight='normal')
        self.font_main = font.Font(family='Ariel', size=base_font_size, weight='normal')
        self.font_main_ul = font.Font(family='Ariel', size=base_font_size, weight='normal', underline=True)
        self.font_main_hdr = font.Font(family='Ariel', size=int(base_font_size * 1.25), weight='normal')
        self.font_main_bold = font.Font(family='Ariel', size=base_font_size, weight='bold')
        self.font_console = font.Font(family='Courier', size=base_font_size, weight='normal')

        # ---- Treeview styling ----
        style = ttk.Style()
        style.theme_use("clam")  # important for predictable styling

        # Remove outer frame/border completely
        style.layout(
            "Treeview",
            [("Treeview.treearea", {"sticky": "nswe"})]
        )
        style.configure("Treeview", relief="flat")
        style.map(
            "Treeview",
            background=[("selected", "#6699ff")],
            foreground=[("selected", "white")],
        )
        style.configure(
            "Treeview",
            font=self.font_main,
            rowheight=22
        )
        style.configure(
            "Treeview.Heading",
            background="white",
            foreground="black",
            font=self.font_main_bold,
            relief="flat",
            borderwidth=0,
            padding=(6, 4)
        )