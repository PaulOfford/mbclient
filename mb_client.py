import threading

from mb_gui import *
from backend import *
from js8call_driver import *
from status import *


class MbClient:

    last_check_for_updates = 0
    f2b_q = queue.Queue(maxsize=20)  # queue for messages from the frontend to the backend
    b2f_q = queue.Queue(maxsize=20)  # queue for messages to the frontend from the backend
    comms_tx_q = queue.Queue(maxsize=20)  # queue for messages from the backend to the comms driver
    comms_rx_q = queue.Queue(maxsize=20)  # queue for messages to the backend from the comms driver
    be_t = None  # thread anchor
    comms_t = None  # thread anchor
    header = None
    main = None

    def __init__(self):
        # start backend thread
        backend = Backend(self.f2b_q, self.b2f_q, self.comms_tx_q, self.comms_rx_q)
        self.be_t = threading.Thread(target=backend.backend_loop)
        self.be_t.start()

        comms = Js8CallDriver(self.comms_tx_q, self.comms_rx_q)
        self.comms_t = threading.Thread(target=comms.run_comms)
        self.comms_t.start()

    def status_check(self):
        # we have had a message from the backend -> check for updated sections
        status = Status()

        if status.hdr_updated > status.last_checked:
            self.header.reload_header()

        if status.latest_updated > status.last_checked:
            self.main.reload_latest()

        if status.qso_updated > status.last_checked:
            self.main.reload_qso_box()

        if status.cli_updated > status.last_checked:
            self.main.reload_cli()
            logging.logmsg(4, "reload_cli()")

        if status.blogs_updated > status.last_checked:
            self.main.reload_blog_list()
            logging.logmsg(4, "reload_blog_list()")

        status.update_last_checked()

    def process_updates(self):

        try:
            msg = self.b2f_q.get(block=False)  # if no msg waiting, this will throw an exception
            logging.logmsg(3, f"fe: {msg}")
            self.status_check()
            self.b2f_q.task_done()
        except queue.Empty:
            pass

        root.after(200, self.process_updates)

    def client_shutdown(self):
        be_sig = GuiMessage()
        be_sig.set_cmd('X')
        be_sig.set_cli_input('MB Client Shutdown')
        be_sig.set_op('exit')
        self.f2b_q.put(be_sig)

        comms_sig = CommsMessage()
        comms_sig.set_ts(time.time())
        comms_sig.set_direction('tx')
        comms_sig.set_typ('control')
        comms_sig.set_target('set')
        comms_sig.set_obj('exit')
        self.comms_tx_q.put(comms_sig)

        self.comms_t.join(1)  # wait for up to one second for the comms thread to exit
        self.be_t.join(1)  # wait for up to one second for the backend thread to exit

        root.destroy()

    def set_frequency(self, freq):
        req = GuiMessage()
        req.set_cmd('S')
        req.set_frequency(freq)
        req.set_ts()
        self.f2b_q.put(req)
        logging.logmsg(3, f"fe: {req}")

        pass

    def run_client(self):

        # set up the menu bar
        top_menu = tk.Menu(root)
        root.config(menu=top_menu)

        file_menu = tk.Menu(top_menu)
        top_menu.add_cascade(label='File', menu=file_menu)
        file_menu.add_command(label='Settings    F2', command=lambda:settings_window())
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.client_shutdown)

        band_menu = tk.Menu(top_menu)
        top_menu.add_cascade(label='Band', menu=band_menu)
        band_menu.add_command(label='160m:   1.842 000 MHz', command=ft.partial(self.set_frequency, 1842000))
        band_menu.add_command(label='80m:    3.578 000 MHz', command=ft.partial(self.set_frequency, 3578000))
        band_menu.add_command(label='40m:    7.708 000 MHz', command=ft.partial(self.set_frequency, 7078000))
        band_menu.add_command(label='30m:    10.130 000 MHz', command=ft.partial(self.set_frequency, 10130000))
        band_menu.add_command(label='17m:    18.104 000 MHz', command=ft.partial(self.set_frequency, 18104000))
        band_menu.add_command(label='15m:    21.078 000 MHz', command=ft.partial(self.set_frequency, 21078000))
        band_menu.add_command(label='12m:    24.922 000 MHz', command=ft.partial(self.set_frequency, 24922000))
        band_menu.add_command(label='10m:    28.078 000 MHz', command=ft.partial(self.set_frequency, 28078000))
        band_menu.add_command(label='6m:     50.318 000 MHz', command=ft.partial(self.set_frequency, 50318000))
        band_menu.add_command(label='2m:     144.178 000 MHz', command=ft.partial(self.set_frequency, 144178000))

        # we need to ensure closing the window stops the backend
        root.protocol("WM_DELETE_WINDOW", self.client_shutdown)

        frame_container = tk.Frame(root)
        frame_container.pack(fill='both', expand=1, side='top', anchor='n')

        frame_hdr = tk.Frame(frame_container, background="black", height=100, pady=10)
        frame_hdr.pack(fill='x', side='top', anchor='n')
        self.header = GuiHeader(header_frame=frame_hdr)  # populate the header

        frame_main = tk.Frame(frame_container, pady=4)
        frame_main.pack(fill=tk.BOTH, expand=1, side='top', anchor='n', padx=4)

        self.header.clock_tick()

        self.main = GuiMain(frame=frame_main, f2b_q=self.f2b_q, b2f_q=self.b2f_q)  # populate the main area

        self.main.reload_qso_box()

        self.main.reload_blog_list()

        root.after(200, self.process_updates)
        root.mainloop()


if __name__ == "__main__":
    c = MbClient()
    c.run_client()
