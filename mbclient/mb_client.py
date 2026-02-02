import time
import threading
import shutil
from queue import Queue
from mbclient.logging_config import setup_logging
import logging
from mbclient.mb_database import MbDatabase
from mbclient.mb_gui import GuiMain
from mbclient.backend import Backend
from mbclient.js8call_driver import Js8CallDriver
setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

class MbClient:
    be_t = None
    comms_t = None
    main = None

    def __init__(self):
        backend = Backend()
        self.be_t = threading.Thread(target=backend.backend_loop)
        self.be_t.start()
        comms = Js8CallDriver()
        self.comms_t = threading.Thread(target=comms.run_comms)
        self.comms_t.start()

    def start_gui(self):
        self.main = GuiMain()
        self.comms_t.join(1)
        self.be_t.join(1)

    def run(self):
        """Backward-compatible entrypoint; starts the GUI."""
        return self.start_gui()


def main():
    """Run MbClient (includes database migration checks)."""
    new_db = MbDatabase()
    db_version = new_db.determine_version()
    logger.info(f'mb_client: Database version: {db_version}')
    if db_version == 0:
        new_db.create()
    elif db_version == 1:
        backup_file = new_db.db_file + time.strftime('.%Y%m%d_%H%M%S', time.gmtime())
        shutil.copy2(new_db.db_file, f'{backup_file}')
        logger.info(f'mb_client: Created database backup {backup_file}')
        new_db.migrate_from_v1()
        logger.info('mb_client: Database conversion complete')
    elif db_version == 2:
        pass
    else:
        raise Exception(f'Unable to determine the version of the database {new_db.db_file}')
    logger.info('mb_client: Database is ready to go')
    c = MbClient()
    c.start_gui()

if __name__ == '__main__':
    main()
