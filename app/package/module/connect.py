'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-08-09 20:40:16
LastEditors: htang
LastEditTime: 2025-08-15 10:18:27
'''
# -*- coding: UTF-8 -*-

import logging
import pymysql
from app.config import db_config

class ConnectMysqlHandler:
  def connect_mysql():
    try:
      # 连接数据库
      db = pymysql.connect(**db_config)
      return db
    except Exception as ex:
      logging.warning("数据库连接失败：", ex)
      return None