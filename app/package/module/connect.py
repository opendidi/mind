"""
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-08-09 20:40:16
LastEditors: htang
LastEditTime: 2025-08-15 10:18:27
"""

# -*- coding: UTF-8 -*-

import json
import logging

import pymysql
from dbutils.pooled_db import PooledDB

from app.config import db_config

_pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    maxcached=5,
    blocking=True,
    ping=1,
    **db_config,
)


class ConnectMysqlHandler:
    def connect_mysql():
        return _pool.connection()


def generic_modify(connect, id, user_id, table, **kwargs):
    """Shared generic UPDATE helper.

    Args:
        connect: An active MySQL connection from ConnectMysqlHandler.connect_mysql().
        id: The primary key value of the row to update.
        user_id: The user_id value to enforce row ownership.
        table: The table name (e.g. "material", "blueprint").
        **kwargs: Column name -> value pairs to set.

    Returns:
        (True, rowcount) on success.
        (False, error_message) on failure.
    """
    if not id:
        logging.warning("ID 不能为空")
        return False, "ID 不能为空"

    if not kwargs:
        logging.warning("没有可更新的字段")
        return False, "没有可更新的字段"

    try:
        with connect.cursor() as cursor:
            for key in kwargs:
                if isinstance(kwargs[key], dict):
                    kwargs[key] = json.dumps(kwargs[key], ensure_ascii=False)

            update_fields = [f"{key} = %s" for key in kwargs.keys()]
            values = list(kwargs.values())

            sql = f"UPDATE {table} SET {', '.join(update_fields)} WHERE id = %s AND user_id = %s"
            values.append(id)
            values.append(user_id)

            cursor.execute(sql, values)
            connect.commit()

            if cursor.rowcount == 0:
                return False, "未找到匹配的 ID 或数据未变更"
            return True, cursor.rowcount
    except Exception as ex:
        logging.warning(f"generic_modify 更新失败：{ex}")
        return False, str(ex)
