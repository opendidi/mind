"""
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-08-09 20:40:16
LastEditors: htang
LastEditTime: 2025-08-15 10:18:27
"""

# -*- coding: UTF-8 -*-

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
