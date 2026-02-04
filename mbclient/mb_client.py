import time
import threading
import shutil
import logging
import sys
import argparse

from .logging_setup import configure_logging
from .mb_database import MbDatabase
from .mb_gui import GuiMain
from .backend import Backend
from . import js8call_driver

from .js8call_driver import Js8CallDriver


from .config import SETTINGS
msg_terminator = SETTINGS.msg_terminator
LOG_LEVEL: int = SETTINGS.log_level
LOG_FILE: str = SETTINGS.log_file
LOG_TO_FILE: bool = SETTINGS.log_to_file
LOG_MAX_BYTES: int = SETTINGS.log_max_bytes
LOG_BACKUP_COUNT: int = SETTINGS.log_backup_count

configure_logging(level=logging.INFO)
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
    """Application entry point.

    Supports optional CLI flags to override logging configuration.
    """

    parser = argparse.ArgumentParser(prog="mbserver", add_help=True)
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default=None,
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL or numeric).",
    )
    parser.add_argument(
        "--log-file",
        dest="log_file",
        default=None,
        help="Path to rotating log file. Overrides config.ini [logging] log_file.",
    )
    parser.add_argument(
        "--no-log-file",
        dest="no_log_file",
        action="store_true",
        help="Disable file logging even if enabled in config.ini.",
    )
    parser.add_argument(
        "--max-log-bytes",
        dest="max_log_bytes",
        type=int,
        default=None,
        help="Rotate log file after this many bytes. Overrides config.ini [logging] log_max_bytes.",
    )
    parser.add_argument(
        "--log-backups",
        dest="log_backups",
        type=int,
        default=None,
        help="Number of rotated log files to keep. Overrides config.ini [logging] log_backup_count.",
    )
    parser.add_argument(
        "--tcp-port",
        dest="tcp_port",
        type=int,
        default=None,
        help="The TCP port number that JS8Call is listening to for a connection from MbServer",
    )

    args = parser.parse_args(sys.argv[1:])

    def _parse_level(v: str) -> int:
        if v is None:
            return int(LOG_LEVEL)
        s = str(v).strip()
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
        name = s.upper()
        if not hasattr(logging, name):
            raise SystemExit(f"Invalid --log-level: {v}")
        lvl = getattr(logging, name)
        if not isinstance(lvl, int):
            raise SystemExit(f"Invalid --log-level: {v}")
        return int(lvl)

    level = _parse_level(args.log_level)

    # Decide file logging
    if args.no_log_file:
        log_file = None
    elif args.log_file is not None:
        log_file = args.log_file
    else:
        log_file = LOG_FILE if LOG_TO_FILE else None

    max_bytes = int(args.max_log_bytes) if args.max_log_bytes is not None else int(LOG_MAX_BYTES)
    backup_count = int(args.log_backups) if args.log_backups is not None else int(LOG_BACKUP_COUNT)

    # Configure application logging (console + optional rotating file, UTC timestamps)
    configure_logging(
        level=level,
        terminator=msg_terminator,
        log_file=log_file,
        max_bytes=max_bytes,
        backup_count=backup_count,
        console=True,
    )

    if args.tcp_port is not None:
        host, _ = SETTINGS.server
        js8call_driver.js8call_addr = (host, args.tcp_port)
        logger.info(
            f"Overriding JS8Call TCP port: {host}:{args.tcp_port}"
        )

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
