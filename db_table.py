import os
import re
import sqlite3

from logging import logmsg
from db_root import db_path


def get_db_file_spec():
    path = os.path.normpath(db_path)
    result = path.split(os.sep)
    resolved_path = ''

    # does the path start with an env variable
    env = re.findall(r"^%([.\w-]+)%$", result[0])
    if len(env) > 0:
        result[0] = os.getenv(env[0])

        if result[0] is None:
            logmsg(1, "Invalid environmental variable in db_root.py")
            exit(99)
        elif not os.path.isdir(result[0]):
            logmsg(1, "Environmental variable in db_root.py points to a non-existent path")
            exit(99)

    # reconstruct the total path
    for element in result:
        resolved_path += element + os.sep

    os.makedirs(resolved_path, 777, True)

    return resolved_path + "mblog.db"


class DbTable:

    col_names = None
    result = None
    has_is_selected = False

    def __init__(self, table):
        self.table = table

        db = sqlite3.connect(get_db_file_spec())
        db.row_factory = sqlite3.Row
        c = db.cursor()
        query = f"SELECT * FROM {table} LIMIT 1"
        c.execute(query)
        logmsg(3, query)
        row = c.fetchone()
        if row:
            self.col_names = row.keys()
            if 'is_selected' in self.col_names:
                self.has_is_selected = True

        c.close()

    # This method returns a list of dictionaries with the columns selected by the
    # hdr_list, in the order of the columns in the hdr_list.
    # The hdr_list must contain a key db_col with a value of the name of a database column.
    def select(self, where=None, group_by=None, order_by=None, desc=False, limit=0, hdr_list=None):

        db = sqlite3.connect(get_db_file_spec())
        c = db.cursor()

        select_cols = ''
        for i, hdr_col in enumerate(hdr_list):
            if i > 0:
                select_cols += ','
            select_cols += f" {hdr_col}"

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

        logmsg(3, query)

        c.execute(query)
        list_of_tuples = c.fetchall()
        db.close()

        result = [{} for _ in range(0, len(list_of_tuples))]

        # convert the list of tuples to a list of dictionaries based on the self.col_names values
        for y, row in enumerate(list_of_tuples):
            for x, col in enumerate(hdr_list):
                abc = f"{col}"
                result[y][abc] = row[x]

        return result

    # This method returns a list of dictionaries with the columns selected by the
    # hdr_list, in the order of the columns in the hdr_list.
    # The hdr_list must contain a key db_col with a value of the name of a database column.
    def select_latest(self, where=None, group_by=None, order_by=None, order='ASC', limit=0, hdr_list=None):

        db = sqlite3.connect(get_db_file_spec())
        c = db.cursor()

        select_cols = ''
        for i, hdr_col in enumerate(hdr_list):
            if i > 0:
                select_cols += ','
            select_cols += f" {hdr_col}"

        # we need a query of the form
        # SELECT * FROM (SELECT ... ORDER BY order_by DESC LIMIT limit) ORDER BY order_by ASC;
        query = "SELECT * FROM ("
        query += f"SELECT {select_cols} FROM {self.table}"

        if where:
            query += f" WHERE {where}"
        if group_by:
            query += f" GROUP BY {group_by}"
        if order_by:
            query += f" ORDER BY {order_by}"

        # ToDo: should the following line be under the "if order_by:" check i.e. indented
        query += " DESC"
        query += f" LIMIT {limit}"
        query += f") ORDER BY {order_by} {order}"

        logmsg(3, query)

        c.execute(query)
        list_of_tuples = c.fetchall()
        db.close()

        result = [{} for _ in range(0, len(list_of_tuples))]

        # convert the list of tuples to a list of dictionaries based on the self.col_names values
        for y, row in enumerate(list_of_tuples):
            for x, col in enumerate(hdr_list):
                abc = f"{col}"
                result[y][abc] = row[x]

        return result

    def update(self, where=None, value_dictionary=None):
        db = sqlite3.connect(get_db_file_spec())
        db.row_factory = sqlite3.Row
        c = db.cursor()

        key_list = list(value_dictionary.keys())
        query = f"UPDATE {self.table} SET "
        for i, key in enumerate(key_list):
            value = value_dictionary[key]

            if i > 0:
                query += ", "

            try:
                int(value)  # this tests for int and float values
                query += f"{key}={value}"
            except ValueError:
                query += f"{key}='{value}'"

        if where:
            query += f" WHERE {where}"

        logmsg(2, query)

        with db:
            c.execute(query)

        db.close()

    def insert(self, row: dict):
        db = sqlite3.connect(get_db_file_spec())
        db.row_factory = sqlite3.Row
        c = db.cursor()

        values = ""

        for column in row:
            if len(values) > 0:
                values += f", "

            if isinstance(row[column], str):
                temp = row[column].replace("'", "''")  # double quote any quotes in the string
                values += f"'{temp}'"
            else:
                values += f"{row[column]}"

        query = f"INSERT INTO {self.table} VALUES ({values})"
        logmsg(2, query)

        with db:
            c.execute(query)

        db.close()

    def delete(self, where=None):

        db = sqlite3.connect(get_db_file_spec())
        c = db.cursor()

        query = f"DELETE FROM {self.table}"
        if where:
            query += f" WHERE {where}"

        logmsg(2, query)

        with db:
            c.execute(query)

        db.close()

        return
