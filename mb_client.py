import threading

from queue import Empty
from mb_gui import *
from backend import *
from status import *


class MbClient:

    last_check_for_updates = 0
    f2b_q = queue.Queue(maxsize=20)
    b2f_q = queue.Queue(maxsize=20)
    header = None
    main = None

    def process_updates(self):

        try:
            msg = self.b2f_q.get(block=False)  # if no msg waiting, this will throw an exception
            print(msg)

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
                print("reload_cli()")

            if status.blogs_updated > status.last_checked:
                self.main.reload_blog_list()
                print("reload_blog_list()")

            status.update_last_checked()
            self.b2f_q.task_done()

        except queue.Empty:
            pass

        root.after(200, self.process_updates)

    def run_client(self):
        # put queues here
        # start backend thread
        backend = Backend()
        t = threading.Thread(target=backend.backend_loop, args=[self.f2b_q, self.b2f_q])
        t.start()

        frame_container = tk.Frame(root)
        frame_container.pack(fill='x', expand=1, side='top', anchor='n')

        frame_hdr = tk.Frame(frame_container, background="black", height=100, pady=10)
        frame_hdr.pack(fill='x', expand=1, side='top', anchor='n')
        self.header = GuiHeader(header_frame=frame_hdr, f2b_q=self.f2b_q, b2f_q=self.b2f_q)  # populate the header

        frame_main = tk.Frame(frame_container, pady=4)
        frame_main.pack(fill='both', expand=1, side='top', anchor='n', padx=4)

        self.header.clock_tick()

        self.main = GuiMain(frame=frame_main, f2b_q=self.f2b_q, b2f_q=self.b2f_q)  # populate the main area

        self.main.reload_qso_box()

        self.main.reload_blog_list()

        root.after(200, self.process_updates)
        root.mainloop()


if __name__ == "__main__":
    c = MbClient()
    c.run_client()
