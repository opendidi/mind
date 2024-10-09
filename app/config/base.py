'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-04-29 17:06:03
LastEditors: htang
LastEditTime: 2024-10-09 09:00:43
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
  'db': 'krpano',
  # 指定DictCursor
  'cursorclass': pymysql.cursors.DictCursor
}