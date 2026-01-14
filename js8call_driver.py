# USE OF THIS PROGRAM
# This is proof of concept program code and is freely available for experimentation.  You can change and
# reuse any portion of the program code without restriction.  The author(s) accept no responsibility for
# damage to equipment, corruption of data or consequential loss caused by this program code or any variant
# of it.  The author(s) accept no responsibility for violation of any radio or amateur radio regulations
# resulting from the use of the program code.
from socket import socket, AF_INET, SOCK_STREAM
import queue

import logging
from status import Status
from message_q import CommsMessage
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
        # the following block of code provides a socket recv with a 10-second timeout
        # we need this so that we call the @MB announcement code periodically
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
        logger.debug('send: ' + message)

        if len(args) > 1 and debug:
            logger.debug('MB message not sent as we are in debug mode')
            # this avoids hamlib errors in JS8Call if the radio isn't connected
        else:
            self.sock.send((message + '\n').encode())   # newline suffix is required

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

    def process_comms_tx(self, message: CommsMessage):
        # message = {'ts': 0.0, 'req_ts': 0.0, 'direction': '', 'source': "", 'destination': "", 'frequency': 0,
        #            'snr': 0, 'typ': "", 'target': '', 'obj': "", 'payload': "", 'rc': 0}

        if message.get_typ() == 'control':
            if message.get_target() == 'set':
                if message.get_obj() == 'exit':
                    exit(0)
                elif message.get_obj() == 'radio_frequency':
                    self.set_radio_frequency(int(message.get_payload()))
        elif message.get_typ() == 'mb_req':
            req_msg = f"{message.get_destination()} {message.get_payload()}"
            self.js8call_api.send('TX.SEND_MESSAGE', req_msg)
            pass
        else:
            logger.error(f"Invalid message received from backend, typ = {message.get_typ()}")

    def process_tx_q(self, timeout: float = 0.05):
        """Process outbound messages from the backend.

        Uses a short blocking wait (reduces CPU) and then drains any burst.
        """
        try:
            comms_tx: CommsMessage = self.comms_tx_q.get(timeout=timeout)
        except queue.Empty:
            return

        try:
            logger.debug(f"js8drv: debug: {comms_tx.get_payload()}")
            self.process_comms_tx(comms_tx)
        finally:
            self.comms_tx_q.task_done()

        # Drain any queued burst without blocking.
        while True:
            try:
                comms_tx = self.comms_tx_q.get_nowait()
            except queue.Empty:
                break
            try:
                logger.debug(comms_tx.get_payload())
                self.process_comms_tx(comms_tx)
            finally:
                self.comms_tx_q.task_done()

    def signal_frontend(self, ts: float, target_object: str, payload: str):
        self.comms_rx_q.put(CommsMessage.signal_frontend(ts, target_object, payload))

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
                    self.signal_frontend(time.time(), 'rx_indicator', 'flash_rx_stop')
                    self.rx_ind_timeout = 0

                for message in messages:
                    logger.info('rx - ' + str(message))
                    typ = message.get('type', '')
                    value = message.get('value', '')
                    params = message.get('params', {})

                    self.signal_frontend(float(params.get('_ID')) / 1000, 'rx_indicator', 'flash_rx_start')
                    self.rx_ind_timeout = time.time() + self.flash_duration

                    if not typ:
                        continue

                    elif typ == 'RIG.PTT':
                        if value == 'on':
                            payload = 'ptt_on'
                        else:
                            payload = 'ptt_off'

                        logger.debug(f"Received {payload}")
                        self.signal_frontend(float(params.get('_ID')) / 1000, 'tx_indicator', payload)

                    elif typ == 'STATION.CALLSIGN':
                        logger.debug(f"Received {value}")

                        ts = float(params.get('_ID')) / 1000
                        self.comms_rx_q.put(CommsMessage.control_status(ts, 'callsign', value))

                    elif typ == 'RIG.FREQ':
                        logger.debug(f"Received {value}")

                        ts = float(params.get('_ID')) / 1000
                        dial = int(params['DIAL'])
                        off = int(params['OFFSET'])

                        self.comms_rx_q.put(
                            CommsMessage.control_status(ts, 'radio_frequency', str(dial), frequency=dial, offset=off)
                        )
                        logger.debug('q_put: REG_FREQ - radio_frequency: ' + str(dial))

                        self.comms_rx_q.put(
                            CommsMessage.control_status(ts, 'offset', str(off), frequency=dial, offset=off)
                        )
                        logger.debug('q_put: REG_FREQ - offset: ' + str(off))

                    elif typ == 'STATION.STATUS':
                        logger.debug(f"STATION.STATUS is {value}")

                        ts = float(params.get('_ID')) / 1000
                        dial = int(params['DIAL'])
                        off = int(params['OFFSET'])

                        self.comms_rx_q.put(
                            CommsMessage.control_status(ts, 'radio_frequency', str(dial), frequency=dial, offset=off)
                        )
                        logger.debug('q_put: STATION.STATUS - radio_frequency: ' + str(dial))

                        self.comms_rx_q.put(
                            CommsMessage.control_status(ts, 'offset', str(off), frequency=dial, offset=off)
                        )
                        logger.debug('q_put: STATION.STATUS - offset: ' + str(off))

                    elif typ == 'RX.DIRECTED':  # we are only interested in messages directed to us, including @MB
                        logger.debug('rx - ' + str(message))
                        ts = float(params['UTC']) / 1000
                        dial = int(params['DIAL'])
                        snr = int(params['SNR'])

                        # if we haven't got the callsign, yet we need to wait
                        self.status.reload_status()
                        while self.status.callsign == "Pending":
                            time.sleep(0.2)
                            self.status.reload_status()

                        if params['TO'] == self.status.callsign:
                            mb_typ = 'mb_rsp'
                        else:
                            mb_typ = 'mb_notify'

                        self.comms_rx_q.put(
                            CommsMessage.mb_rx(
                                ts,
                                params['FROM'],
                                params['TO'],
                                frequency=dial,
                                snr=snr,
                                typ=mb_typ,
                                payload=(message['value']).strip(),
                            )
                        )

        finally:
            self.js8call_api.close()
