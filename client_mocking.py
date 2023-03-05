import time


sample_msgs = [
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
    {
        "params":
            {
                "CMD": " ", "DIAL": 14078000, "EXTRA": "", "FREQ": 14079646, "FROM": "M0PXO", "GRID": "",
                "OFFSET": 1646, "SNR": -2, "SPEED": 1, "TDRIFT": 0.80000001192092896,
                "TEXT": "M0PXO: 2E0FGO  +E25~\\"
                       "n25 - 2023-01-20 - FALCONSAT-3 NEARS REENTRY",
                "TO": "2E0FGO", "UTC": 1678041207751, "_ID": -1
            },
        "type": "RX.DIRECTED",
        "value": "M0PXO: 2E0FGO  +E25~\n"
                "25 - 2023-01-20 - FALCONSAT-3 NEARS REENTRY"
    }
]

count = 0


def js8call_mock_listen():
    global count
    time.sleep(0.1)
    if count <= 0:
        count += 1
        return sample_msgs
    return []
