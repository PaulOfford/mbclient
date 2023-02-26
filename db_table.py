import sqlite3

import logging
from db_root import *


class DbTable:

    col_names = None
    result = None
    has_is_selected = False

    def __init__(self, table):
        self.table = table

        db = sqlite3.connect(db_file)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        query = f"SELECT * FROM {table} LIMIT 1"
        c.execute(query)
        logging.logmsg(3, query)
        row = c.fetchone()
        self.col_names = row.keys()
        if 'is_selected' in self.col_names:
            self.has_is_selected = True

        c.close()

    # This method returns a list of dictionaries with the columns selected by the
    # hdr_list, in the order of the columns in the hdr_list.
    # The hdr_list must contain a key db_col with a value of the name of a database column.
    def select(self, where=None, order_by=None, desc=False, limit=0, group_by=None, hdr_list=None):

        db = sqlite3.connect(db_file)
        c = db.cursor()

        select_cols = ''
        for i, hdr_col in enumerate(hdr_list):
            if i > 0:
                select_cols += ','
            select_cols += f" {hdr_col['db_col']}"

        query = f"SELECT {select_cols} FROM {self.table}"
        if where:
            query += f" WHERE {where}"
        if group_by:
            query += f" GROUP BY {group_by}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if desc:
            query += f" DESC"
        if limit > 0:
            query += f" LIMIT {limit}"

        logging.logmsg(3, query)

        c.execute(query)
        list_of_tuples = c.fetchall()
        db.close()

        result = [{} for _ in range(0, len(list_of_tuples))]

        # convert the list of tuples to a list of dictionaries based on the self.col_names values
        for y, row in enumerate(list_of_tuples):
            for x, col in enumerate(hdr_list):
                abc = f"{col['db_col']}"
                result[y][abc] = row[x]

        return result

    def update(self, where=None, value_dictionary=None):
        db = sqlite3.connect(db_file)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        key = list(value_dictionary.keys())[0]
        value = value_dictionary[key]

        try:
            value_int = int(value)
            query = f"UPDATE {self.table} SET {key}={value_int}"
        except ValueError:
            query = f"UPDATE {self.table} SET {key}='{value}'"

        if where:
            query += f" WHERE {where}"
        with db:
            c.execute(query)
            logging.logmsg(3, query)

    def insert(self, row: dict):
        db = sqlite3.connect(db_file)
        db.row_factory = sqlite3.Row
        c = db.cursor()

        values = ""

        for column in row:
            if len(values) > 0:
                values += f", "

            if isinstance(row[column], str):
                temp = row[column].replace("'", "''")
                values += f"'{temp}'"
            else:
                values += f"{row[column]}"

        query = f"INSERT INTO {self.table} VALUES ({values})"
        logging.logmsg(3, query)

        with db:
            c.execute(query)
