import time
sample_msgs = [
    {'params': {'_ID': 1686299050534}, 'type': 'STATION.CALLSIGN', 'value': '2E0FGO'},
    {'params': {'DIAL': 0, 'FREQ': 1650, 'OFFSET': 1650, '_ID': 1686299050534}, 'type': 'RIG.FREQ', 'value': ''},
    {'params': {
        'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079652, 'FROM': 'M0PXO', 'GRID': ' JO01',
        'OFFSET': 1652, 'SNR': -1, 'SPEED': 1, 'TDRIFT': 1.2999999523162842, 'TEXT': 'M0PXO: @MB  M0PXO 14 231014',
        'TO': '@MB', 'UTC': 1678314667724, '_ID': -1}, 'type': 'RX.DIRECTED', 'value': 'M0PXO: @MB  M0PXO 14 231014'}
]
count = 0


def js8call_mock_listen():
    global count
    time.sleep(1)
    if count <= 0:
        count += 1
        return sample_msgs
    return []
