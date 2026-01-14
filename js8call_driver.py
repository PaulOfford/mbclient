# USE OF THIS PROGRAM
# This is proof of concept program code and is freely available for experimentation.  You can change and
# reuse any portion of the program code without restriction.  The author(s) accept no responsibility for
# damage to equipment, corruption of data or consequential loss caused by this program code or any variant
# of it.  The author(s) accept no responsibility for violation of any radio or amateur radio regulations
# resulting from the use of the program code.
from socket import socket, AF_INET, SOCK_STREAM
import queue

import logging
logger = logging.getLogger(__name__)

from status import Status
from message_q import CommsMessage
from client_mocking import js8call_mock_listen

import json
import time
import select

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
        logger.info('js8drv: info: Connecting to JS8Call at ' + ':'.join(map(str, js8call_addr)))
        try:
            api = self.sock.connect(js8call_addr)
            self.connected = True
            logger.info('js8drv: info: Connected to JS8Call')
            return api

        except ConnectionRefusedError:
            logger.info('js8drv: err: Connection to JS8Call has been refused.')
            logger.info('js8drv: info: Check that:')
            logger.info('js8drv: info: * JS8Call is running')
            logger.info('js8drv: info: * JS8Call settings check boxes Enable TCP Server API and'
                      'Accept TCP Requests are checked')
            logger.info('js8drv: info: * The API server port number in JS8Call matches the setting in this script'
                      ' - default is 2442')
            logger.info('js8drv: info: * There are no firewall rules preventing the connection')
            exit(1)

    def listen(self):
        # the following block of code provides a socket recv with a 10-second timeout
        # we need this so that we call the @MB announcement code periodically
        messages = []
        self.sock.setblocking(False)
        ready = select.select([self.sock], [], [], 0.5)
        if ready[0]:
            content = self.sock.recv(65500)
            logger.debug('js8drv: recv: ' + str(content))

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
                logger.info('js8drv: ctrl: Connection to JS8Call has closed')
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
        logger.debug('js8drv: send: ' + message)

        if len(args) > 1 and debug:
            logger.debug('js8drv: info: MB message not sent as we are in debug mode')
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
        logger.debug('js8drv: call: RIG.SET_FREQ')
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
            logger.info(f"js8drv: err: Invalid message received from backend, typ = {message.get_typ()}")

    def process_tx_q(self):
        try:
            comms_tx: CommsMessage = self.comms_tx_q.get(block=False)  # if no msg waiting, this will throw an exception
            logger.debug(f"js8drv: debug: {comms_tx.payload}")
            self.process_comms_tx(comms_tx)
            self.comms_tx_q.task_done()
        except queue.Empty:
            pass

        return

    def signal_frontend(self, ts: float, target_object: str, payload: str):
        rx_data = CommsMessage()
        rx_data.set_ts(ts)
        rx_data.set_direction('rx')
        rx_data.set_typ('signal')
        rx_data.set_target('frontend')
        rx_data.set_obj(target_object)
        rx_data.set_payload(payload)
        self.comms_rx_q.put(rx_data)

    def run_comms(self):

        if self.js8call_api.connected:
            logger.debug('js8drv: call: STATION.GET_CALLSIGN')
            self.js8call_api.send('STATION.GET_CALLSIGN', '')

            logger.debug('js8drv: call: RIG.GET_FREQ')
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
                    logger.info('js8drv: recv: ' + str(message))
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

                        logger.debug(f"js8call_driver: Received {payload}")
                        self.signal_frontend(float(params.get('_ID')) / 1000, 'tx_indicator', payload)

                    elif typ == 'STATION.CALLSIGN':
                        logger.debug(f"js8call_driver: Received {value}")

                        rx_status_callsign = CommsMessage()
                        rx_status_callsign.set_ts(float(params.get('_ID'))/1000)
                        rx_status_callsign.set_direction('rx')
                        rx_status_callsign.set_typ('control')
                        rx_status_callsign.set_target('status')
                        rx_status_callsign.set_obj('callsign')
                        rx_status_callsign.set_payload(value)
                        self.comms_rx_q.put(rx_status_callsign)

                    elif typ == 'RIG.FREQ':
                        logger.debug(f"js8call_driver: Received {value}")

                        # send message to backend re frequency
                        rx_status_radio_frequency = CommsMessage()
                        rx_status_radio_frequency.set_ts(float(params.get('_ID'))/1000)
                        rx_status_radio_frequency.set_direction('rx')
                        rx_status_radio_frequency.set_typ('control')
                        rx_status_radio_frequency.set_target('status')
                        rx_status_radio_frequency.set_obj('radio_frequency')
                        rx_status_radio_frequency.set_frequency(int(params['DIAL']))
                        rx_status_radio_frequency.set_offset(int(params['OFFSET']))
                        rx_status_radio_frequency.set_payload(str(params['DIAL']))
                        self.comms_rx_q.put(rx_status_radio_frequency)
                        logger.debug('js8drv: q_put: REG_FREQ - radio_frequency: ' + str(params['DIAL']))

                        # send message to backend re offset
                        rx_status_offset = CommsMessage()
                        rx_status_offset.set_ts(float(params.get('_ID'))/1000)
                        rx_status_offset.set_direction('rx')
                        rx_status_offset.set_typ('control')
                        rx_status_offset.set_target('status')
                        rx_status_offset.set_obj('offset')
                        rx_status_offset.set_frequency(int(params['DIAL']))
                        rx_status_offset.set_offset(int(params['OFFSET']))
                        rx_status_offset.set_payload(str(params['OFFSET']))
                        self.comms_rx_q.put(rx_status_offset)
                        logger.debug('js8drv: q_put: REG_FREQ - offset: ' + str(params['OFFSET']))

                    elif typ == 'STATION.STATUS':
                        logger.debug(f"js8call_driver: STATION.STATUS is {value}")

                        # send message to backend re frequency
                        rx_status_radio_frequency = CommsMessage()
                        rx_status_radio_frequency.set_ts(float(params.get('_ID'))/1000)
                        rx_status_radio_frequency.set_direction('rx')
                        rx_status_radio_frequency.set_typ('control')
                        rx_status_radio_frequency.set_target('status')
                        rx_status_radio_frequency.set_obj('radio_frequency')
                        rx_status_radio_frequency.set_frequency(int(params['DIAL']))
                        rx_status_radio_frequency.set_offset(int(params['OFFSET']))
                        rx_status_radio_frequency.set_payload(str(params['DIAL']))
                        self.comms_rx_q.put(rx_status_radio_frequency)
                        logger.debug('js8drv: q_put: STATION.STATUS - radio_frequency: ' + str(params['DIAL']))

                        # send message to backend re offset
                        rx_status_offset = CommsMessage()
                        rx_status_offset.set_ts(float(params.get('_ID'))/1000)
                        rx_status_offset.set_direction('rx')
                        rx_status_offset.set_typ('control')
                        rx_status_offset.set_target('status')
                        rx_status_offset.set_obj('offset')
                        rx_status_offset.set_frequency(int(params['DIAL']))
                        rx_status_offset.set_offset(int(params['OFFSET']))
                        rx_status_offset.set_payload(str(params['OFFSET']))
                        self.comms_rx_q.put(rx_status_offset)
                        logger.debug('js8drv: q_put: STATION.STATUS - offset: ' + str(params['OFFSET']))

                    elif typ == 'RX.DIRECTED':  # we are only interested in messages directed to us, including @MB
                        logger.debug('comms: recv: ' + str(message))
                        rx_mb_msg = CommsMessage()

                        rx_mb_msg.set_ts(float(params['UTC'])/1000)
                        rx_mb_msg.set_direction('rx')
                        rx_mb_msg.set_source(params['FROM'])
                        rx_mb_msg.set_destination(params['TO'])
                        rx_mb_msg.set_frequency(params['DIAL'])
                        rx_mb_msg.set_snr(params['SNR'])

                        # if we haven't got the callsign, yet we need to wait
                        self.status.reload_status()
                        while self.status.callsign == "Pending":
                            time.sleep(0.2)
                            self.status.reload_status()

                        if params['TO'] == self.status.callsign:
                            rx_mb_msg.set_typ('mb_rsp')
                        else:
                            rx_mb_msg.set_typ('mb_notify')

                        rx_mb_msg.set_target('mb_client')
                        rx_mb_msg.set_obj('receiver')
                        rx_mb_msg.set_payload((message['value']).strip())
                        self.comms_rx_q.put(rx_mb_msg)

        finally:
            self.js8call_api.close()
