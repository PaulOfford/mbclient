import re
from socket import socket, AF_INET, SOCK_STREAM
import queue
import logging
from mbclient.general_functions import add_progress_m
from mbclient.status import Status
from mbclient.message_q import b2c_q, c2b_q, UnifiedMessage, MessageType, MessageVerb, MessageParameter
from mbclient.client_mocking import js8call_mock_listen
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
            logger.error('* JS8Call settings check boxes Enable TCP Server API andAccept TCP Requests are checked')
            logger.error('* The API server port number in JS8Call matches the setting in this script - default is 2442')
            logger.error('* There are no firewall rules preventing the connection')
            exit(1)

    def listen(self):
        messages = []
        self.sock.setblocking(False)
        ready = select.select([self.sock], [], [], 0.5)
        if ready[0]:
            content = self.sock.recv(65500)
            logger.debug('rx - ' + str(content))
            if content:
                content = content.replace(bytes('♢', 'utf8'), bytes('', 'utf8'))
                content = content.replace(bytes("  '}", 'utf8'), bytes("'}", 'utf8'))
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
        return messages

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
        message = message.replace('\n\n', '\n \n')
        if len(args) > 1 and debug:
            logger.debug('MB message not sent as we are in debug mode')
        else:
            mb_msg = (message + '\n').encode()
            logger.debug('tx - ' + str(mb_msg))
            self.sock.send(mb_msg)

    def close(self):
        self.sock.close()

class Js8CallDriver:
    status = None
    request = None
    rx_ind_timeout: float = 0.0
    flash_duration = 0.5

    def __init__(self):
        self.status = Status()
        self.js8call_api = Js8CallApi()
        self.js8call_api.connect()

    def set_radio_frequency(self, freq: int):
        logger.debug('call: RIG.SET_FREQ')
        kwargs = {'params': {'DIAL': freq}}
        self.js8call_api.send('RIG.SET_FREQ', **kwargs)
        pass

    def process_mb_msg(self, message: UnifiedMessage):
        req_msg = f'{message.get_param(MessageParameter.DESTINATION)} {message.get_param(MessageParameter.MB_MSG)}'
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
            logger.error(f'Invalid message received from backend, typ = {message.get_typ()}')

    def process_tx_q(self, timeout: float=0.05):
        """Process outbound messages from the backend.

        Uses a short blocking wait (reduces CPU) and then drains any burst.
        """
        try:
            comms_tx: UnifiedMessage = b2c_q.get(timeout=timeout)
        except queue.Empty:
            return
        try:
            logger.debug(f'Received from BACKEND: {comms_tx.get_params()}')
            self.process_comms_tx(comms_tx)
            add_progress_m(comms_tx)
        finally:
            b2c_q.task_done()

    @staticmethod
    def signal_frontend(verb: MessageVerb):
        m = UnifiedMessage.create(target='FRONTEND', typ='SIGNAL', verb=verb)
        c2b_q.put(m)

    @staticmethod
    def signal_backend(verb: MessageVerb, param):
        m = UnifiedMessage.create(target='BACKEND', typ='SIGNAL', verb=verb, params=param)
        c2b_q.put(m)

    @staticmethod
    def inform_backend(source: str, frequency: int, destination: str, mb_message: str):
        m = UnifiedMessage.create(target='BACKEND', typ='MB_MSG', verb='INFORM', params={'source': source, 'destination': destination, 'mb_msg': mb_message, 'frequency': frequency})
        c2b_q.put(m)
        add_progress_m(m)

    @staticmethod
    def announce_to_backend(source: str, frequency: int, destination: str, mb_message: str):
        m = UnifiedMessage.create(target='BACKEND', typ='MB_MSG', verb='ANNOUNCE', params={'source': source, 'destination': destination, 'mb_msg': mb_message, 'frequency': frequency})
        c2b_q.put(m)
        add_progress_m(m)

    def run_comms(self):
        if self.js8call_api.connected:
            logger.debug('Send STATION.GET_CALLSIGN')
            self.js8call_api.send('STATION.GET_CALLSIGN', '')
            logger.debug('Send RIG.GET_FREQ')
            self.js8call_api.send('RIG.GET_FREQ', '')
        try:
            while self.js8call_api.connected:
                self.process_tx_q()
                if mock:
                    messages = js8call_mock_listen()
                else:
                    messages = self.js8call_api.listen()
                if 0 < self.rx_ind_timeout < time.time():
                    self.signal_frontend(MessageVerb.FLASH_RX_STOP)
                    self.rx_ind_timeout = 0
                for message in messages:
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
                        self.signal_frontend(verb)
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
                        msg_elements = re.findall('^\\S+: +\\S+ +([\\S\\s]+)', value)
                        mb_message = msg_elements[0]
                        if str(params['TO']) == '@MB':
                            self.announce_to_backend(str(params['FROM']), int(params['DIAL']), str(params['TO']), mb_message)
                        else:
                            self.inform_backend(str(params['FROM']), int(params['DIAL']), str(params['TO']), mb_message)
                        logger.debug('q_put: INFORM - ' + mb_message)
        finally:
            self.js8call_api.close()