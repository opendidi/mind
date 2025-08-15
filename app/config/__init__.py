'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2025-07-09 14:19:33
LastEditors: htang
LastEditTime: 2025-08-15 10:17:31
'''
# -*- coding: UTF-8 -*-

import pymysql
import pymysql.cursors

# 数据库连接参数
db_config = {
  # 数据库主机地址
  'host': 'localhost',
  # 数据库用户名
  'user': 'root',
  # 数据库密码
  'passwd': 'root123',
  # 端口
  'port': 3306,
  # 数据库
  'db': 'mind',
  # 指定DictCursor
  'cursorclass': pymysql.cursors.DictCursor
}