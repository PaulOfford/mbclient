import os
import re
import sqlite3
import logging
from mbclient.db_root import db_path
logger = logging.getLogger(__name__)


def get_db_file_spec():
    path = os.path.normpath(db_path)
    result = path.split(os.sep)
    resolved_path = ''
    env = re.findall('^%([.\\w-]+)%$', result[0])
    if len(env) > 0:
        result[0] = os.getenv(env[0])
        if result[0] is None:
            logger.info('Invalid environmental variable in db_root.py')
            exit(99)
        elif not os.path.isdir(result[0]):
            logger.info('Environmental variable in db_root.py points to a non-existent path')
            exit(99)
    for element in result:
        resolved_path += element + os.sep
    os.makedirs(resolved_path, 777, True)
    return resolved_path + 'mblog.db'


class DbTable:
    col_names = None
    result = None
    has_is_selected = False

    def __init__(self, table):
        self.table = table
        db = sqlite3.connect(get_db_file_spec())
        db.row_factory = sqlite3.Row
        c = db.cursor()
        query = f'SELECT * FROM {table} LIMIT 1'
        c.execute(query)
        logger.debug(query)
        row = c.fetchone()
        if row:
            self.col_names = row.keys()
            if 'is_selected' in self.col_names:
                self.has_is_selected = True
        c.close()

    def select(self, where=None, group_by=None, order_by=None, desc=False, limit=0, hdr_list=None):
        db = sqlite3.connect(get_db_file_spec())
        c = db.cursor()
        select_cols = ''
        for i, hdr_col in enumerate(hdr_list):
            if i > 0:
                select_cols += ','
            select_cols += f' {hdr_col}'
        query = f'SELECT {select_cols} FROM {self.table}'
        if where:
            query += f' WHERE {where}'
        if group_by:
            query += f' GROUP BY {group_by}'
        if order_by:
            query += f' ORDER BY {order_by}'
        if desc:
            query += f' DESC'
        if limit > 0:
            query += f' LIMIT {limit}'
        logger.debug(query)
        c.execute(query)
        list_of_tuples = c.fetchall()
        db.close()
        result = [{} for _ in range(0, len(list_of_tuples))]
        for y, row in enumerate(list_of_tuples):
            for x, col in enumerate(hdr_list):
                abc = f'{col}'
                result[y][abc] = row[x]
        return result

    def select_latest(self, where=None, group_by=None, order_by=None, limit=0, hdr_list=None):
        db = sqlite3.connect(get_db_file_spec())
        c = db.cursor()
        select_cols = ''
        for i, hdr_col in enumerate(hdr_list):
            if i > 0:
                select_cols += ','
            select_cols += f' {hdr_col}'
        query = 'SELECT * FROM ('
        query += f'SELECT {select_cols} FROM {self.table}'
        if where:
            query += f' WHERE {where}'
        if group_by:
            query += f' GROUP BY {group_by}'
        if order_by:
            query += f' ORDER BY {order_by}'
        query += ' DESC'
        query += f' LIMIT {limit}'
        query += f') ORDER BY {order_by} ASC'
        logger.debug(query)
        c.execute(query)
        list_of_tuples = c.fetchall()
        db.close()
        result = [{} for _ in range(0, len(list_of_tuples))]
        for y, row in enumerate(list_of_tuples):
            for x, col in enumerate(hdr_list):
                abc = f'{col}'
                result[y][abc] = row[x]
        return result

    def update(self, where=None, value_dictionary=None):
        db = sqlite3.connect(get_db_file_spec())
        db.row_factory = sqlite3.Row
        c = db.cursor()
        key_list = list(value_dictionary.keys())
        query = f'UPDATE {self.table} SET '
        for i, key in enumerate(key_list):
            value = value_dictionary[key]
            if i > 0:
                query += ', '
            try:
                int(value)
                query += f'{key}={value}'
            except ValueError:
                value = value.replace("'", "''")
                query += f"{key}='{value}'"
        if where:
            query += f' WHERE {where}'
        logger.debug(query)
        with db:
            c.execute(query)
        db.close()

    def insert(self, row: dict):
        db = sqlite3.connect(get_db_file_spec())
        db.row_factory = sqlite3.Row
        c = db.cursor()
        values = ''
        for column in row:
            if len(values) > 0:
                values += f', '
            if isinstance(row[column], str):
                temp = row[column].replace("'", "''")
                values += f"'{temp}'"
            else:
                values += f'{row[column]}'
        query = f'INSERT INTO {self.table} VALUES ({values})'
        logger.debug(query)
        with db:
            c.execute(query)
        db.close()

    def delete(self, where=None):
        db = sqlite3.connect(get_db_file_spec())
        c = db.cursor()
        query = f'DELETE FROM {self.table}'
        if where:
            query += f' WHERE {where}'
        logger.debug(query)
        with db:
            c.execute(query)
        db.close()
        return
