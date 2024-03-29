import time


sample_msgs = [
    {'params': {'_ID': 1686299050534}, 'type': 'STATION.CALLSIGN', 'value': '2E0FGO'},
    {'params': {'DIAL': 0, 'FREQ': 1650, 'OFFSET': 1650, '_ID': 1686299050534}, 'type': 'RIG.FREQ', 'value': ''},
    {
        'params': {
            'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079652,
            'FROM': 'M0PXO', 'GRID': ' JO01',
            'OFFSET': 1652, 'SNR': -1, 'SPEED': 1,
            'TDRIFT': 1.2999999523162842,
            'TEXT': 'M0PXO: @MB  M0PXO 14 2023-10-14',
            'TO': '@MB', 'UTC': 1678314667724, '_ID': -1
        },
        'type': 'RX.DIRECTED',
        'value': 'M0PXO: @MB  M0PXO 14 2023-10-14'
    },
    # {
    #     'params': {
    #         'CMD': ' HEARTBEAT', 'DIAL': 14078010, 'EXTRA': '', 'FREQ': 14078697,
    #         'FROM': 'YJ9MX5IVS', 'GRID': 'RF77',
    #         'OFFSET': 687, 'SNR': -20, 'SPEED': 1,
    #         'TDRIFT': -1.5,
    #         'TEXT': 'YJ9MX5IVS: @MB AUSNEW 407 2023-03-08',
    #         'TO': '@MB',
    #         'UTC': 1677341768425,
    #         '_ID': -1
    #     },
    #     'type': 'RX.DIRECTED',
    #     'value': 'YJ9MX5IVS: @MB AUSNEW 407 2023-03-08'
    # },
    # {
    #     'params': {
    #         'CMD': ' ', 'DIAL': 14078010, 'EXTRA': '', 'FREQ': 14079645,
    #         'FROM': 'M0PXO', 'GRID': '',
    #         'OFFSET': 1635, 'SNR': 2, 'SPEED': 0, 'TDRIFT': 1.5,
    #         'TEXT': 'M0PXO: M7PJO  +E30~\n'
    #                 '30 - 2023-02-27 - OHIO TRAIN DERAILMENT DETAILS',
    #         'TO': 'M7PJO',
    #         'UTC': 1678215129000,
    #         '_ID': -1
    #     },
    #     'type': 'RX.DIRECTED',
    #     'value': 'M0PXO: M7PJO  +E30~\n'
    #         '30 - 2023-02-27 - OHIO TRAIN DERAILMENT DETAILS'
    # },
    # {
    #     'params': {
    #         'DIAL': 14078000, 'FREQ': 14079635, 'OFFSET': 1635, 'SELECTED': '', 'SPEED': 1, '_ID': '179793501498'
    #     },
    #     'type': 'STATION.STATUS', 'value': ''
    # },
    # {
    #     'params': {
    #         'BAND': '40m', 'DIAL': 7078000, 'FREQ': 7078811, 'OFFSET': 811, '_ID': -1
    #     },
    #     'type': 'RIG.FREQ', 'value': ''
    # },
    # {'params':
    #     {
    #         'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079650, 'FROM': 'M0PXO', 'GRID': '',
    #         'OFFSET': 1650, 'SNR': 2, 'SPEED': 1, 'TDRIFT': 1.899999976158142,
    #         'TEXT': 'M0PXO: 2E0FGO  -G40~ NOT FOUND  ', 'TO': '2E0FGO', 'UTC': 1679998287584, '_ID': -1
    #     },
    #     'type': 'RX.DIRECTED', 'value': 'M0PXO: 2E0FGO  -G40~ NOT FOUND'
    # },
    # {'params':
    #     {
    #         'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079642, 'FROM': 'M0PXO', 'GRID': '', 'OFFSET': 1642,
    #         'SNR': 0, 'SPEED': 1, 'TDRIFT': 1.7999999523162842, 'TEXT': 'M0PXO: 2E0FGO  +L41~\nNO POSTS FOUND  ',
    #         'TO': '2E0FGO', 'UTC': 1680001087402, '_ID': -1
    #     },
    #     'type': 'RX.DIRECTED', 'value': 'M0PXO: 2E0FGO  +L41~\nNO POSTS FOUND  '
    # },
    # {'params':
    #      {
    #          'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079637, 'FROM': 'M0PXO', 'GRID': '', 'OFFSET': 1637,
    #          'SNR': -7, 'SPEED': 1, 'TDRIFT': 0,
    #          'TEXT': 'M0PXO: 2E0FGO  +FG23123~\n28 - 2023-01-26 - YAESU RADIOS DONATED TO ARRL\n29 - 2023-01-27 - RSGB PROPOGATION NEWS  ', 'TO': '2E0FGO', 'UTC': 1683825276770, '_ID': -1}, 'type': 'RX.DIRECTED', 'value': 'M0PXO: 2E0FGO  +FG23123~\n28 - 2023-01-26 - YAESU RADIOS DONATED TO ARRL\n29 - 2023-01-27 - RSGB PROPOGATION NEWS  '
    # },
    # {'params':
    #      {
    #          'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079641, 'FROM': 'M0PXO', 'GRID': '', 'OFFSET': 1641,
    #          'SNR': -2, 'SPEED': 1, 'TDRIFT': 1.7000000476837158,
    #          'TEXT': 'M0PXO: 2E0FGO  +G28~\nYAESU USA HAS DONATED AN FTDX101MP AND FTDX10, BOTH HF/50 MHZ TRANSCEIVERS.\n\nTHE YAESU FTDX101MP TRANSCEIVER IS A WELCOME ADDITION TO STUDIO 1 IN W1AW, THE HIRAM PERCY MAXIM MEMORIAL STATION.  ', 'TO': '2E0FGO', 'UTC': 1683902846777, '_ID': -1}, 'type': 'RX.DIRECTED', 'value': 'M0PXO: 2E0FGO  +G28~\nYAESU USA HAS DONATED AN FTDX101MP AND FTDX10, BOTH HF/50 MHZ TRANSCEIVERS.\n\nTHE YAESU FTDX101MP TRANSCEIVER IS A WELCOME ADDITION TO STUDIO 1 IN W1AW, THE HIRAM PERCY MAXIM MEMORIAL STATION.  '
    # },
    # {'params':
    #      {
    #          'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079641, 'FROM': 'M0PXO', 'GRID': '', 'OFFSET': 1641,
    #          'SNR': -2, 'SPEED': 1, 'TDRIFT': 1.7000000476837158,
    #          'TEXT': 'M0PXO: 2E0FGO  +FG22C31~\n21 - 2023-01-06 - MORE HAMS ON THE ISS\n22 - 2023-01-13 - HAARP THANKS HAMS\n23 - 2023-01-13 - K7RA SOLAR UPDATE\n24 - 2023-01-15 - RSGB PROPOGATION NEWS\n25 - 2023-01-20 - FALCONSAT-3 NEARS REENTRY  ', 'TO': '2E0FGO', 'UTC': 1683909306710, '_ID': -1}, 'type': 'RX.DIRECTED', 'value': 'M0PXO: 2E0FGO  +FG22C31~\n21 - 2023-01-06 - MORE HAMS ON THE ISS\n22 - 2023-01-13 - HAARP THANKS HAMS\n23 - 2023-01-13 - K7RA SOLAR UPDATE\n24 - 2023-01-15 - RSGB PROPOGATION NEWS\n25 - 2023-01-20 - FALCONSAT-3 NEARS REENTRY  '
    # },

    # {
    #     'params': {
    #         'CMD': ' ', 'DIAL': 14078010, 'EXTRA': '', 'FREQ': 14079645,
    #         'FROM': 'M0PXO', 'GRID': '',
    #         'OFFSET': 1635, 'SNR': 2, 'SPEED': 0, 'TDRIFT': 1.5,
    #         'TEXT': 'M0PXO: 2E0FGO  +LG0~\n'
    #                 '20 - MARINES TO GAIN RADIO OP EXPERIENCE\n'
    #                 '21 - MORE HAMS ON THE ISS\n'
    #                 '22 - HAARP THANKS HAMS\n'
    #                 '23 - K7RA SOLAR UPDATE\n'
    #                 '24 - RSGB PROPOGATION NEWS ♢ ',
    #         'TO': '2E0FGO',
    #         'UTC': 1677342252288,
    #         '_ID': -1
    #     },
    #     'type': 'RX.DIRECTED',
    #     'value': 'M0PXO: 2E0FGO  +LG0~\n'
    #         '20 - MARINES TO GAIN RADIO OP EXPERIENCE\n'
    #         '21 - MORE HAMS ON THE ISS\n'
    #         '22 - HAARP THANKS HAMS\n'
    #         '23 - K7RA SOLAR UPDATE\n'
    #         '24 - RSGB PROPOGATION NEWS ♢ '
    # },
    # {
    #     'params':
    #         {
    #             'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079644,
    #             'FROM': 'M0PXO', 'GRID': '',
    #             'OFFSET': 1644, 'SNR': -2, 'SPEED': 1, 'TDRIFT': 0.800000011920929,
    #             'TEXT': 'M0PXO: 2E0FGO  +L25,26,27,28,29~\n'
    #                     '25 - FALCONSAT-3 NEARS REENTRY\n'
    #                     '26 - 2026 WORLD RADIOSPORT TEAM CHAMPIONSHIP NEWS\n'
    #                     '27 - RSGB PROPOGATION NEWS\n'
    #                     '28 - YAESU RADIOS DONATED TO ARRL\n'
    #                     '29 - RSGB PROPOGATION NEWS  ',
    #             'TO': '2E0FGO', 'UTC': 1678030607661, '_ID': -1
    #         },
    #     'type': 'RX.DIRECTED',
    #     'value': 'M0PXO: 2E0FGO  +L25,26,27,28,29~\n'
    #             '25 - FALCONSAT-3 NEARS REENTRY\n'
    #             '26 - 2026 WORLD RADIOSPORT TEAM CHAMPIONSHIP NEWS\n'
    #             '27 - RSGB PROPOGATION NEWS\n'
    #             '28 - YAESU RADIOS DONATED TO ARRL\n'
    #             '29 - RSGB PROPOGATION NEWS'
    # },
    # {
    #     "params":
    #         {
    #             "CMD": " ", "DIAL": 14078000, "EXTRA": "", "FREQ": 14079646, "FROM": "M0PXO", "GRID": "",
    #             "OFFSET": 1646, "SNR": -2, "SPEED": 1, "TDRIFT": 0.80000001192092896,
    #             "TEXT": "M0PXO: 2E0FGO  +E25~\\"
    #                    "n25 - 2023-01-20 - FALCONSAT-3 NEARS REENTRY",
    #             "TO": "2E0FGO", "UTC": 1678041207751, "_ID": -1
    #         },
    #     "type": "RX.DIRECTED",
    #     "value": "M0PXO: 2E0FGO  +E25~\n"
    #             "25 - 2023-01-20 - FALCONSAT-3 NEARS REENTRY"
    # },
    # {
    #     'params':
    #         {
    #             'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079647, 'FROM': 'M0PXO', 'GRID': '',
    #             'OFFSET': 1647, 'SNR': -3, 'SPEED': 1, 'TDRIFT': 3.0999999046325684,
    #             'TEXT': 'M0PXO: 2E0FGO  +G29~\n'
    #                     'AS OF THURSDAY, WE HAD A STRANGE SITUATION WHEREBY ALL THE CURRENT VISIBLE SUNSPOTS WERE '
    #                     'IN ONE HEMISPHERE OF THE SUN. BUT THIS ISN\'T THAT UNUSUAL, AS THE TWO HEMISPHERES USUALLY '
    #                     'PEAK AT DIFFERENT TIMES IN THE CYCLE.\n\n'
    #                     'THE SOLAR FLUX INDEX DECLINED AND STOOD AT 172 ON THE 26 JANUARY.  ',
    #             'TO': '2E0FGO', 'UTC': 1678195788783, '_ID': -1
    #         },
    #     'type': 'RX.DIRECTED',
    #     'value': 'M0PXO: 2E0FGO  +G29~\n'
    #              'AS OF THURSDAY, WE HAD A STRANGE SITUATION WHEREBY ALL THE CURRENT VISIBLE SUNSPOTS WERE '
    #              'IN ONE HEMISPHERE OF THE SUN. BUT THIS ISN\'T THAT UNUSUAL, AS THE TWO HEMISPHERES USUALLY '
    #              'PEAK AT DIFFERENT TIMES IN THE CYCLE.\n\n'
    #              'THE SOLAR FLUX INDEX DECLINED AND STOOD AT 172 ON THE 26 JANUARY.  '
    # },
    # {
    #     'params':
    #         {
    #             'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079647, 'FROM': 'M0PXO', 'GRID': '',
    #             'OFFSET': 1647, 'SNR': -3, 'SPEED': 1, 'TDRIFT': 3.0999999046325684,
    #             'TEXT': 'M0PXO: M7PJO  +G23~\n'
    #                     'THE K7RA SOLAR UPDATE\n\n'
    #                     '2023-01-13\n'
    #                     'WOW! Sunspot numbers up, geomagnetic disturbances down. What could be better? '
    #                     'Okay, maybe Solar Cycle 19, but that was 66 years ago and by far the all time largest.\n\n'
    #                     'But this is now, we are in Solar Cycle 25, and this sunspot cycle is emerging better '
    #                     'than the consensus forecast. It is predicted to peak about 30 months from now in Summer 2025.',
    #             'TO': 'M7PJO', 'UTC': 1678195788783, '_ID': -1
    #         },
    #     'type': 'RX.DIRECTED',
    #     'value': 'M0PXO: M7PJO  +G23~\n'
    #             'THE K7RA SOLAR UPDATE\n\n'
    #             '2023-01-13\n'
    #             'WOW! SUNSPOT NUMBERS UP, GEOMAGNETIC DISTURBANCES DOWN. WHAT COULD BE BETTER? '
    #             'OKAY, MAYBE SOLAR CYCLE 19, BUT THAT WAS 66 YEARS AGO AND BY FAR THE ALL TIME LARGEST.\n\n'
    #             'BUT THIS IS NOW, WE ARE IN SOLAR CYCLE 25, AND THIS SUNSPOT CYCLE IS EMERGING BETTER '
    #             'THAN THE CONSENSUS FORECAST. IT IS PREDICTED TO PEAK ABOUT 30 MONTHS FROM NOW IN SUMMER 2025.',
    # },
    # {
    #     'params':
    #         {
    #             'CMD': ' ', 'DIAL': 14078000, 'EXTRA': '', 'FREQ': 14079642, 'FROM': 'M0PXO', 'GRID': '',
    #             'OFFSET': 1642, 'SNR': -6, 'SPEED': 0, 'TDRIFT': 0.5,
    #             'TEXT': 'M0PXO: 2E0FGO  +WX~\n'
    #                     'MAY 15 2023 06:56\n'
    #                     'LATTITUDE; 2750.02N\n'
    #                     'LONGITIDE: 08131.02W\n'
    #                     'WIND DIRECTION: 107\n'
    #                     'WIND SPEED: 000\n'
    #                     'WIND GUST: 000\n'
    #                     'TEMPERATURE: 065\n'
    #                     'RAIN: 000\nHUMIDITY: 97\n'
    #                     'SOLAR RADIATION: 0016\n'
    #                     'PRESSURE: 1019  ',
    #             'TO': '2E0FGO', 'UTC': 1696078032169, '_ID': -1
    #         },
    #     'type': 'RX.DIRECTED',
    #     'value': 'M0PXO: 2E0FGO  +WX~\n'
    #              'MAY 15 2023 06:56\n'
    #              'LATTITUDE; 2750.02N\n'
    #              'LONGITIDE: 08131.02W\n'
    #              'WIND DIRECTION: 107\n'
    #              'WIND SPEED: 000\n'
    #              'WIND GUST: 000\n'
    #              'TEMPERATURE: 065\n'
    #              'RAIN: 000\n'
    #              'HUMIDITY: 97\n'
    #              'SOLAR RADIATION: 0016\n'
    #              'PRESSURE: 1019  '
    # },
]

count = 0


def js8call_mock_listen():
    global count
    time.sleep(1)
    if count <= 0:
        count += 1
        return sample_msgs
    return []
