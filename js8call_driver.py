# USE OF THIS PROGRAM
# This is proof of concept program code and is freely available for experimentation.  You can change and
# reuse any portion of the program code without restriction.  The author(s) accept no responsibility for
# damage to equipment, corruption of data or consequential loss caused by this program code or any variant
# of it.  The author(s) accept no responsibility for violation of any radio or amateur radio regulations
# resulting from the use of the program code.
import re
from socket import socket, AF_INET, SOCK_STREAM
import queue

import logging
from status import Status
from message_q import UnifiedMessage, MessageType, MessageTarget, MessageVerb, MessageOperator, MessageParameter
from client_mocking import js8call_mock_listen

import json
import time
import select

logger = logging.getLogger(__name__)

js8call_addr = ('127.0.0.1', 2442)
debug = False
mock = False


class Js8CallApi:

    connected = False
    my_station = ''
    my_grid = ''

    def __init__(self):
        self.sock = socket(AF_INET, SOCK_STREAM)

    def connect(self):
        logger.info('Connecting to JS8Call at ' + ':'.join(map(str, js8call_addr)))
        try:
            api = self.sock.connect(js8call_addr)
            self.connected = True
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
                self.connected = False
                logger.info('ctrl: Connection to JS8Call has closed')
                # ToDo: signal connection loss to backend, which should then add a QSO box entry

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

        if len(args) > 1 and debug:
            logger.debug('MB message not sent as we are in debug mode')
            # this avoids hamlib errors in JS8Call if the radio isn't connected
        else:
            mb_msg = (message + '\n').encode()
            logger.debug('send: ' + str(mb_msg))
            self.sock.send(mb_msg)   # newline suffix is required

    # def set_rig_freq(self, freq):

    def close(self):
        self.sock.close()


class Js8CallDriver:

    status = None
    request = None
    comms_tx_q = None
    comms_rx_q = None

    rx_ind_timeout: float = 0.0
    flash_duration = 0.5

    def __init__(self, comms_tx_q: queue.Queue, comms_rx_q: queue.Queue):
        self.status = Status()
        self.comms_tx_q = comms_tx_q
        self.comms_rx_q = comms_rx_q
        self.js8call_api = Js8CallApi()
        self.js8call_api.connect()

    def set_radio_frequency(self, freq: int):
        logger.debug('call: RIG.SET_FREQ')
        kwargs = {'params': {'DIAL': freq}}
        self.js8call_api.send('RIG.SET_FREQ', **kwargs)
        pass

    def process_mb_msg(self, message: UnifiedMessage):
        req_msg = f"{message.get_param(MessageParameter.DESTINATION)} {message.get_param(MessageParameter.MB_MSG)}"
        self.js8call_api.send('TX.SEND_MESSAGE', req_msg)

    def process_control(self, message: UnifiedMessage):
        if message.get_verb() == MessageVerb.SHUTDOWN:
            exit(0)
        elif message.get_verb() == MessageVerb.SET_FREQ:
            self.set_radio_frequency(message.get_param(MessageParameter.FREQUENCY))
        elif message.get_verb() == MessageVerb.GET_FREQ:
            self.js8call_api.send('RIG.GET_FREQ', '')
        elif message.get_verb() == MessageVerb.GET_OFFSET:
            self.js8call_api.send('RIG.GET_FREQ', '')
        elif message.get_verb() == MessageVerb.GET_CALLSIGN:
            self.js8call_api.send('STATION.GET_CALLSIGN', '')

    def process_comms_tx(self, message: UnifiedMessage):
        if message.get_typ() == MessageType.MB_MSG:
            self.process_mb_msg(message)

        elif message.get_typ() == MessageType.CONTROL:
            self.process_control(message)

        else:
            logger.error(f"Invalid message received from backend, typ = {message.get_typ()}")

    def process_tx_q(self, timeout: float = 0.05):
        """Process outbound messages from the backend.

        Uses a short blocking wait (reduces CPU) and then drains any burst.
        """
        try:
            comms_tx: UnifiedMessage = self.comms_tx_q.get(timeout=timeout)
        except queue.Empty:
            return

        try:
            logger.debug(f"js8drv: debug: {comms_tx.get_params()}")
            self.process_comms_tx(comms_tx)
        finally:
            self.comms_tx_q.task_done()

        # Drain any queued burst without blocking.
        while True:
            try:
                comms_tx = self.comms_tx_q.get(timeout=timeout)
            except queue.Empty:
                break
            try:
                logger.debug(comms_tx.get_params())
                self.process_comms_tx(comms_tx)
            finally:
                self.comms_tx_q.task_done()

    def signal_frontend(self, verb: MessageVerb):
        # These are the signa verbs we can send to the FRONTEND:
        #   FLASH_RX_START, FLASH_RX_STOP, FLASH_TX_START, FLASH_TX_STOP, SCAN_OFF
        m = UnifiedMessage()
        m.set_many(target=MessageTarget.FRONTEND, typ=MessageType.SIGNAL, verb=verb)
        self.comms_rx_q.put(m)

    def signal_backend(self, verb: MessageVerb, param):
        # These are the signal verbs we can send to the FRONTEND:
        #   NOTE_FREQ, NOTE_OFFSET, NOTE_CALLSIGN
        m = UnifiedMessage()
        m.set_many(
            target=MessageTarget.BACKEND,
            typ=MessageType.SIGNAL,
            verb=verb,
            params=param
        )
        self.comms_rx_q.put(m)

    def inform_backend(self, source: str, frequency: int, destination: str, mb_message: str):
        # This is where we send an inbound microblog message to the backend
        m = UnifiedMessage()
        m.set_many(
            target=MessageTarget.BACKEND, typ=MessageType.MB_MSG, verb=MessageVerb.INFORM,
            params={
                MessageParameter.SOURCE: source,
                MessageParameter.DESTINATION: destination,
                MessageParameter.MB_MSG: mb_message,
                MessageParameter.FREQUENCY: frequency
            }
        )
        self.comms_rx_q.put(m)

    def announce_to_backend(self, source: str, frequency: int, destination: str, mb_message: str):
        # This is where we send an inbound microblog message to the backend
        m = UnifiedMessage()
        m.set_many(
            target=MessageTarget.BACKEND, typ=MessageType.MB_MSG, verb=MessageVerb.ANNOUNCE,
            params={
                MessageParameter.SOURCE: source,
                MessageParameter.DESTINATION: destination,
                MessageParameter.MB_MSG: mb_message,
                MessageParameter.FREQUENCY: frequency
            }
        )
        self.comms_rx_q.put(m)

    def run_comms(self):

        if self.js8call_api.connected:
            logger.debug('Send STATION.GET_CALLSIGN')
            self.js8call_api.send('STATION.GET_CALLSIGN', '')

            logger.debug('Send RIG.GET_FREQ')
            self.js8call_api.send('RIG.GET_FREQ', '')

        try:
            while self.js8call_api.connected:

                # process messages from the backend
                self.process_tx_q()

                if mock:
                    messages = js8call_mock_listen()
                else:
                    # process messages from Js8Call
                    messages = self.js8call_api.listen()

                if 0 < self.rx_ind_timeout < time.time():
                    self.signal_frontend(MessageVerb.FLASH_RX_STOP)
                    self.rx_ind_timeout = 0

                for message in messages:
                    logger.debug('rx - ' + str(message))
                    js8call_msg_type = message.get('type', '')
                    value = message.get('value', '')
                    params = message.get('params', {})

                    self.signal_frontend(MessageVerb.FLASH_RX_START)
                    self.rx_ind_timeout = time.time() + self.flash_duration

                    if not js8call_msg_type:
                        continue

                    elif js8call_msg_type == 'RIG.PTT':
                        if value == 'on':
                            verb = MessageVerb.FLASH_TX_START
                        else:
                            verb = MessageVerb.FLASH_TX_STOP

                        logger.debug(f"Received {verb}")
                        self.signal_frontend(verb)

                    elif js8call_msg_type == 'STATION.CALLSIGN':
                        logger.debug(f"Received {value}")
                        self.signal_backend(MessageVerb.NOTE_CALLSIGN, {'callsign': value})

                    elif js8call_msg_type == 'RIG.FREQ' or js8call_msg_type == 'STATION.STATUS':
                        logger.debug(f"Received {value}")

                        dial = int(params['DIAL'])
                        offset = int(params['OFFSET'])

                        self.signal_backend(MessageVerb.NOTE_FREQ, {'frequency': dial})
                        logger.debug('q_put: NOTE_FREQ - ' + str(dial))

                        self.signal_backend(MessageVerb.NOTE_OFFSET, {'offset': offset})
                        logger.debug('q_put: NOTE_OFFSET - ' + str(offset))

                    elif js8call_msg_type == 'RX.DIRECTED':
                        logger.debug('rx - ' + str(message))

                        # We need to extract the source and destination
                        msg_elements = re.findall(r"^\S+: +\S+ +([\S\s]+)", value)
                        mb_message = msg_elements[0]

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

        finally:
            self.js8call_api.close()
