from __future__ import annotations
import re
from socket import socket, AF_INET, SOCK_STREAM
from queue import Queue, Empty
from dataclasses import dataclass, field
import logging
import json
import time
import select

from .general_functions import add_progress_m
from .message_q import b2c_q_p0, b2c_q_p1, c2b_q, UnifiedMessage, MessageType, MessageVerb, MessageParameter
from .config import SETTINGS

js8call_addr = SETTINGS.server
DEBUG = SETTINGS.debug
MAX_QUEUE_SIZE = SETTINGS.max_queue_size
QUEUE_GET_TIMEOUT = 0
RELEASE_TIME_INCREMENT = SETTINGS.release_time_increment
RELEASE_TIME_INCREMENT_SHORT = SETTINGS.release_time_increment_short
AGE_OUT_TIME = SETTINGS.age_out_time
SEND_BLOCK_TIME = 60  # This is the number of seconds we must wait before sending to the same station

logger = logging.getLogger(__name__)


@dataclass
class Station:
    callsign: str
    absolute_frequency: int
    tx_release_time: float
    tx_q: Queue[UnifiedMessage] = field(default_factory=Queue)


class Js8CallApi:

    my_station = ''
    my_grid = ''

    def __init__(self):
        self.sock = socket(AF_INET, SOCK_STREAM)

    def connect(self):
        logger.info('Connecting to JS8Call at ' + ':'.join(map(str, js8call_addr)))
        try:
            api = self.sock.connect(js8call_addr)
            logger.info('Connected to JS8Call')
            return api

        except ConnectionRefusedError:
            logger.error('Connection to JS8Call has been refused.')
            logger.error('Check that:')
            logger.error('* JS8Call is running')
            logger.error(
                '* JS8Call settings check boxes Enable TCP Server API and'
                'Accept TCP Requests are checked'
            )
            logger.error(
                '* The API server port number in JS8Call matches the setting in this script'
                ' - default is 2442'
            )
            logger.error('* There are no firewall rules preventing the connection')
            exit(1)

    def listen(self):
        # the following block of code provides a socket recv with a 0.5-second timeout
        messages = []
        self.sock.setblocking(False)
        ready = select.select([self.sock], [], [], 0.5)
        if ready[0]:
            content = self.sock.recv(65500)
            logger.debug('rx - ' + str(content))

            if content:
                # remove the terminator
                content = content.replace(bytes('♢', 'utf8'), bytes('', 'utf8'))
                content = content.replace(bytes("  '}", 'utf8'), bytes("'}", 'utf8'))
                # we have to tidy the content in case there are multiple responses in a single socket recv
                content = content.replace(bytes('}\n{', 'utf8'), bytes('},{', 'utf8'))
                content = bytes('[', 'utf8') + content
                content += bytes(']', 'utf8')
                content = content.replace(bytes('}\n]', 'utf8'), bytes('}]', 'utf8'))
                try:
                    messages = json.loads(content)
                except ValueError:
                    pass
            else:
                logger.info('Connection to JS8Call has closed')
                messages.append({'type': 'DISCONNECT'})

        return messages  # we return a list of messages, typically with a length of one

    @staticmethod
    def to_message(typ, value='', params=None):
        if params is None:
            params = {}
        return json.dumps({'type': typ, 'value': value, 'params': params})

    def send(self, *args, **kwargs):
        params = kwargs.get('params', {})
        if '_ID' not in params:
            params['_ID'] = '{}'.format(int(time.time() * 1000))
            kwargs['params'] = params
        message = self.to_message(*args, **kwargs)

        message = message.replace('\n\n', '\n \n')  # this seems to help with the JS8Call message window format

        if len(args) > 1 and DEBUG:
            logger.debug('MB message not sent as we are in debug mode')
            # this avoids hamlib errors in JS8Call if the radio isn't connected
        else:
            mb_msg = (message + '\n').encode()
            logger.debug('tx - ' + str(mb_msg))
            self.sock.send(mb_msg)   # newline suffix is required

    def close(self):
        self.sock.close()


class Js8CallDriver:

    status = None
    request = None
    rx_ind_timeout: float = 0.0
    rx_duration = 0.5

    ptt_release_time: float = 0.0

    is_connected = False

    station_list: list[Station] = []
    # Entries in the station_list are Station objects

    def __init__(self):
        self.js8call_api = Js8CallApi()
        self.js8call_api.connect()
        self.is_connected = True

        # We need to add a special-case entry to the station_list
        # to allow the queuing of send messages for stations we haven't seen
        # before.
        self.station_list.append(
            Station(
                callsign="UNSEEN",
                absolute_frequency=0,
                tx_release_time=0,
                tx_q=Queue(maxsize=MAX_QUEUE_SIZE)
            )
        )

    def set_radio_frequency(self, freq: int):
        logger.debug('call: RIG.SET_FREQ')
        kwargs = {'params': {'DIAL': freq}}
        self.js8call_api.send('RIG.SET_FREQ', **kwargs)
        pass

    def process_mb_msg(self, m: UnifiedMessage):
        req_msg = f"{m.get_param(MessageParameter.DESTINATION)} {m.get_param(MessageParameter.MB_MSG)}"
        self.js8call_api.send('TX.SEND_MESSAGE', req_msg)

    def process_control(self, m: UnifiedMessage):
        if m.get_verb() == MessageVerb.SHUTDOWN:
            self.is_connected = False
            return
        elif m.get_verb() == MessageVerb.SET_FREQ:
            self.set_radio_frequency(m.get_param(MessageParameter.FREQUENCY))
        elif m.get_verb() == MessageVerb.GET_FREQ:
            self.js8call_api.send('RIG.GET_FREQ', '')
        elif m.get_verb() == MessageVerb.GET_OFFSET:
            self.js8call_api.send('RIG.GET_FREQ', '')
        elif m.get_verb() == MessageVerb.GET_CALLSIGN:
            self.js8call_api.send('STATION.GET_CALLSIGN', '')

    def process_comms_tx(self, m: UnifiedMessage):
        if m.get_typ() == MessageType.MB_MSG:
            # We can only send if we are not awaiting completion of a previous send.
            if time.time() > self.ptt_release_time:
                self.process_mb_msg(m)

        elif m.get_typ() == MessageType.CONTROL:
            self.process_control(m)

        else:
            logger.error(f"Invalid message received from backend, typ = {m.get_typ()}")

    def add_to_station_list(self, callsign: str, absolute_frequency: int) -> None:
        self.station_list.append(
            Station(
                callsign=callsign,
                absolute_frequency=absolute_frequency,
                tx_release_time=time.time() + RELEASE_TIME_INCREMENT,
                tx_q=Queue(maxsize=MAX_QUEUE_SIZE)
            )
        )

    def check_the_station_list(self, callsign: str) -> int:
        for i, station in enumerate(self.station_list):
            if station.callsign == callsign:
                return i
        return 0  # Remember the 'UNSEEN' entry is always the first entry

    def update_station_list_entry(self, callsign: str, absolute_frequency: int) -> None:
        index = self.check_the_station_list(callsign=callsign)
        if index == 0:
            # We didn't find the callsign in the station list
            self.add_to_station_list(callsign=callsign, absolute_frequency=absolute_frequency)
            return

        self.station_list[index].absolute_frequency = absolute_frequency
        self.station_list[index].tx_release_time = time.time() + RELEASE_TIME_INCREMENT
        return

    def age_out_stations(self) -> None:
        # This function isn't perfect.  If we have two adjacent entries in station_list to be aged out
        # we will miss the second.  It's not critical that we age entries out during the first pass
        # as we will do so with subsequent passes.
        for i, station in enumerate(self.station_list):
            if i == 0:  # We don't want to age out the 'UNSEEN' entry at index 0
                continue
            if self.station_list[i].tx_release_time < (time.time() - AGE_OUT_TIME):
                self.station_list.pop(i)

    def update_tx_release_time(self, callsign: str, absolute_frequency: int) -> None:
        if bool(callsign) == bool(absolute_frequency):
            raise ValueError("Provide exactly one of callsign or absolute_frequency")

        if callsign:
            index = self.check_the_station_list(callsign=callsign)
            self.station_list[index].tx_release_time = time.time() + RELEASE_TIME_INCREMENT
            return

        if absolute_frequency:
            for station in self.station_list:
                if station.absolute_frequency == absolute_frequency:
                    station.tx_release_time = time.time() + RELEASE_TIME_INCREMENT

    def process_p0_queue(self) -> None:
        try:
            comms_tx: UnifiedMessage = b2c_q_p0.get(timeout=QUEUE_GET_TIMEOUT)
            logger.debug(f"Received from BACKEND: {comms_tx.get_params()}")
            self.process_comms_tx(comms_tx)
            add_progress_m(comms_tx)
            b2c_q_p0.task_done()

        except Empty:
            return

    def process_p1_queue(self) -> None:
        try:
            comms_tx: UnifiedMessage = b2c_q_p1.get(timeout=QUEUE_GET_TIMEOUT)
            logger.debug(f"Received from BACKEND: {comms_tx.get_params()}")

            # Check if we are sending to a station in the station_list.
            # If the station is not found we will get index = 0, which will get us to the 'UNSEEN' entry.
            index = self.check_the_station_list(comms_tx.get_param(MessageParameter.DESTINATION))
            self.station_list[index].tx_q.put(comms_tx)

            b2c_q_p1.task_done()

        except Empty:
            return

    def process_station_queues(self) -> None:
        if time.time() < self.ptt_release_time:
            return

        for station in self.station_list:
            if time.time() > station.tx_release_time:
                try:
                    comms_tx: UnifiedMessage = station.tx_q.get(timeout=QUEUE_GET_TIMEOUT)
                    logger.info(f"Received from BACKEND: {comms_tx.get_params()}")

                    self.process_comms_tx(comms_tx)

                    # No more send to this station for a while
                    station.tx_release_time = time.time() + RELEASE_TIME_INCREMENT

                    add_progress_m(comms_tx)
                    station.tx_q.task_done()
                    return

                except Empty:
                    continue
        return

    def process_b2c_q(self):
        """Process outbound messages from the backend.
        """
        self.process_p0_queue()
        self.process_p1_queue()
        return

    @staticmethod
    def signal_backend(verb: MessageVerb, param):
        # These are the signal verbs we can send to the FRONTEND:
        #   NOTE_FREQ, NOTE_OFFSET, NOTE_CALLSIGN, NOTE_RX, NOTE_PTT
        m = UnifiedMessage.create(
            priority=0,
            target="BACKEND",
            typ="SIGNAL",
            verb=verb,
            params=param
        )
        c2b_q.put(m)

    @staticmethod
    def inform_backend(source: str, frequency: int, destination: str, mb_message: str):
        # This is where we send an inbound microblog message to the backend
        m = UnifiedMessage.create(
            priority=1,
            target="BACKEND",
            typ="MB_MSG",
            verb="INFORM",
            params={
                "source": source,
                "destination": destination,
                "mb_msg": mb_message,
                "frequency": frequency
            }
        )
        c2b_q.put(m)
        add_progress_m(m)

    @staticmethod
    def announce_to_backend(source: str, frequency: int, destination: str, mb_message: str):
        # This is where we send an inbound microblog message to the backend
        m = UnifiedMessage.create(
            priority=1,
            target="BACKEND",
            typ="MB_MSG",
            verb="ANNOUNCE",
            params={
                "source": source,
                "destination": destination,
                "mb_msg": mb_message,
                "frequency": frequency
            }
        )
        c2b_q.put(m)
        add_progress_m(m)

    def run_comms(self):

        if self.is_connected:
            logger.debug('Send STATION.GET_CALLSIGN')
            self.js8call_api.send('STATION.GET_CALLSIGN', '')

            logger.debug('Send RIG.GET_FREQ')
            self.js8call_api.send('RIG.GET_FREQ', '')

        try:
            while self.is_connected:
                self.process_b2c_q()  # Process messages from the backend.
                self.process_station_queues()  # Process messages to be sent to stations.

                # process messages from Js8Call
                messages = self.js8call_api.listen()

                if 0 < self.rx_ind_timeout < time.time():
                    self.signal_backend(MessageVerb.NOTE_RX, param={MessageParameter.RX: False})
                    self.rx_ind_timeout = 0

                for message in messages:
                    js8call_msg_type = message.get('type', '')
                    value = message.get('value', '')
                    params = message.get('params', {})

                    if self.rx_ind_timeout == 0:
                        self.signal_backend(MessageVerb.NOTE_RX, param={MessageParameter.RX: True})
                    self.rx_ind_timeout = time.time() + self.rx_duration

                    if not js8call_msg_type:
                        continue

                    elif js8call_msg_type == 'DISCONNECT':
                        self.is_connected = False
                        self.signal_backend(MessageVerb.NOTE_DISCONNECT, {})
                        continue

                    elif js8call_msg_type == 'RIG.PTT':
                        if value == 'on':
                            ptt_state = True
                            # We need to wait for the last send to complete
                            self.ptt_release_time = time.time() + RELEASE_TIME_INCREMENT

                        else:
                            ptt_state = False
                            # We need to wait in case there are more frames
                            self.ptt_release_time = time.time() + RELEASE_TIME_INCREMENT

                        self.signal_backend(MessageVerb.NOTE_PTT, {MessageParameter.PTT: ptt_state})

                    elif js8call_msg_type == 'STATION.CALLSIGN':
                        self.signal_backend(MessageVerb.NOTE_CALLSIGN, {'callsign': value})

                    elif js8call_msg_type == 'RIG.FREQ' or js8call_msg_type == 'STATION.STATUS':
                        dial = int(params['DIAL'])
                        offset = int(params['OFFSET'])

                        self.signal_backend(MessageVerb.NOTE_FREQ, {'frequency': dial})
                        logger.debug('q_put: NOTE_FREQ - ' + str(dial))

                        self.signal_backend(MessageVerb.NOTE_OFFSET, {'offset': offset})
                        logger.debug('q_put: NOTE_OFFSET - ' + str(offset))

                    elif js8call_msg_type == 'RX.DIRECTED':
                        logger.debug(f"RX.DIRECTED {value}")
                        # We need to extract the source and destination
                        msg_elements = re.findall(r"^\S+: +\S+ +([\S\s]+)", value)
                        mb_message = msg_elements[0]

                        self.update_station_list_entry(str(params['FROM']), int(params['FREQ']))

                        if str(params['TO']) == "@MB":
                            self.announce_to_backend(
                                str(params['FROM']),
                                int(params['DIAL']),
                                str(params['TO']),
                                mb_message
                            )

                        else:
                            self.inform_backend(
                                str(params['FROM']),
                                int(params['DIAL']),
                                str(params['TO']),
                                mb_message
                            )

                        logger.debug('q_put: INFORM - ' + mb_message)

                    elif js8call_msg_type == 'RX.ACTIVITY':
                        absolute_frequency = int(params['FREQ'])
                        logger.info(f"Seeing RX.ACTIVITY messages for FREQ: {absolute_frequency}")
                        self.update_tx_release_time(callsign='', absolute_frequency=absolute_frequency)

        finally:
            self.js8call_api.close()
