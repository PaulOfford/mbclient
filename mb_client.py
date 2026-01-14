import time
import threading
import shutil
import tkinter as tk
from queue import Queue

from my_logging import logmsg
from mb_database import MbDatabase
from mb_gui import GuiMain
from backend import Backend
from js8call_driver import Js8CallDriver


class MbClient:
    f2b_q = Queue(maxsize=20)  # queue for messages from the frontend to the backend
    b2f_q = Queue(maxsize=20)  # queue for messages to the frontend from the backend
    comms_tx_q = Queue(maxsize=20)  # queue for messages from the backend to the comms driver
    comms_rx_q = Queue(maxsize=20)  # queue for messages to the backend from the comms driver
    be_t = None  # thread anchor
    comms_t = None  # thread anchor

    main = None

    def __init__(self):
        # start backend thread
        backend = Backend(self.f2b_q, self.b2f_q, self.comms_tx_q, self.comms_rx_q)
        self.be_t = threading.Thread(target=backend.backend_loop)
        self.be_t.start()

        comms = Js8CallDriver(self.comms_tx_q, self.comms_rx_q)
        self.comms_t = threading.Thread(target=comms.run_comms)
        self.comms_t.start()

    def start_gui(self):
        self.main = GuiMain(f2b_q=self.f2b_q, b2f_q=self.b2f_q)

        self.comms_t.join(1)  # wait for up to one second for the comms thread to exit
        self.be_t.join(1)  # wait for up to one second for the backend thread to exit


if __name__ == "__main__":
    new_db = MbDatabase()

    db_version = new_db.determine_version()

    logmsg(1, f"mb_client: Database version: {db_version}")

    if db_version == 0:
        new_db.create()

    elif db_version == 1:
        # prompt to ask for a conversion

        # backup the version 1 database
        backup_file = new_db.db_file + time.strftime(".%Y%m%d_%H%M%S", time.gmtime())
        shutil.copy2(new_db.db_file, f"{backup_file}")
        logmsg(1, f"mb_client: Created database backup {backup_file}")

        new_db.migrate_from_v1()
        logmsg(1, "mb_client: Database conversion complete")

    elif db_version == 2:
        pass  # nothing to do

    else:
        raise Exception(f"Unable to determine the version of the database {new_db.db_file}")

    logmsg(1, "mb_client: Database is ready to go")

    c = MbClient()
    c.start_gui()
