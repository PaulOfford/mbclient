from db_table import DbTable


class Status:
    status_cols = [
        'radio_frequency', 'user_frequency', 'offset', 'is_scanning', 'callsign',
    ]

    radio_frequency: int = 0
    user_frequency: int = 0
    offset: int = 0
    is_scanning: bool = False
    callsign: str = ""
    selected_station: str = ""

    def __init__(self):
        self.reload_status()

    def reload_status(self):
        status_table = DbTable('status')
        db_values_list = status_table.select(
            where=None, order_by=None, desc=False,
            limit=1, hdr_list=self.status_cols
        )
        db_values = db_values_list[0]
        self.radio_frequency = db_values['radio_frequency']
        self.user_frequency = db_values['user_frequency']
        self.offset = db_values['offset']
        self.is_scanning = db_values['is_scanning']
        self.callsign = db_values['callsign']

    def set_callsign(self, callsign: str):
        status_table = DbTable('status')
        status_table.update(
            value_dictionary={
                'callsign': callsign
            }
        )
        self.callsign = callsign

    def set_radio_frequency(self, radio_frequency: int):
        status_table = DbTable('status')
        status_table.update(
            value_dictionary={
                'radio_frequency': radio_frequency
            }
        )
        self.radio_frequency = radio_frequency

    def set_user_frequency(self, user_frequency: int):
        status_table = DbTable('status')
        status_table.update(
            value_dictionary={
                'user_frequency': user_frequency
            }
        )
        self.user_frequency = user_frequency

    def set_offset(self, offset: int):
        status_table = DbTable('status')
        status_table.update(
            value_dictionary={
                'offset': offset
            }
        )
        self.offset = offset

    def get_callsign(self) -> str:
        return self.callsign

    def get_radio_frequency(self) -> int:
        return self.radio_frequency

    def get_user_frequency(self) -> int:
        return self.user_frequency

    def get_offset(self) -> int:
        return self.offset

    @staticmethod
    def get_selected_blog_name() -> str:
        post_table = DbTable('blog')
        db_values = post_table.select(
            where="is_selected = 1",
            hdr_list=['blog']
        )

        if len(db_values) == 0:
            return ""

        return db_values[0]['blog']

    @staticmethod
    def get_selected_blog_frequency() -> int:
        post_table = DbTable('blog')
        db_values = post_table.select(
            where="is_selected = 1",
            hdr_list=['frequency']
        )

        if len(db_values) == 0:
            return 0

        return int(db_values[0]['frequency'])

    @staticmethod
    def get_selected_post(blog: str) -> int:
        post_table = DbTable('post')
        db_values = post_table.select(
            where=f"blog='{blog}' AND is_selected = 1",
            hdr_list=['post_id']
        )

        if len(db_values) == 0:
            return 0

        return int(db_values[0]['post_id'])
