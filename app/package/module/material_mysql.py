'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2024-10-08 21:24:11
'''
# -*- coding: UTF-8 -*-

import logging
import pymysql
import pymysql.cursors
import os
from .connect import ConnectMysqlHandler
from app.util.log_config import setup_logging
from datetime import datetime

dirname = os.path.dirname(os.path.abspath(__name__))

# 获取操作系统类型
platform = os.name

if platform == 'nt':
  logger = setup_logging(log_file= dirname + '\\app\\log\\MaterialMysqlHandler.log')

class MaterialMysqlHandler:

  def query_list(material_data):
    page_num = material_data.get('current')
    page_size = material_data.get('page_size')
    keyword = material_data.get('keyword')
    material_type = material_data.get('material_type')
    parent_id = material_data.get('parent_id')
    params = []
    try:
      # 计算起始记录的偏移量
      offset = (int(page_num) - 1) * int(page_size)
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = """
          SELECT
            id, name, pano_id, url, file_path, thumb_path, type, size, extension,
            created_at,
            description,
            parent_id
          FROM
            material
          WHERE
            del = 0
        """
        if material_type is not None:
          sql += "AND type = %s "
          params.append(material_type)
        if parent_id is not None:
          sql += "AND parent_id = %s "
          params.append(parent_id)
        if keyword is not None:
          sql += "AND name LIKE %s "
          params.append('%' + keyword + '%')
        sql += "ORDER BY created_at DESC LIMIT {} OFFSET {}".format(page_size, offset)
        cursor.execute(sql, tuple(params))
        results = cursor.fetchall()
        # 格式化时间
        for row in results:
          # 检查 created_at 的类型
          if isinstance(row['created_at'], str):
            row['created_at'] = datetime.strptime(row['created_at'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y-%m-%d %H:%M:%S')
          elif isinstance(row['created_at'], datetime):
            row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        params_count = []

        count_sql = '''
          SELECT COUNT(*) as total FROM material WHERE del = 0
        '''
        if material_type is not None:
          sql += "AND type = %s "
          params_count.append(material_type)
        if parent_id is not None:
          count_sql += "AND parent_id = %s "
          params_count.append(parent_id)
        if keyword is not None:
          sql += "AND name LIKE %s "
          params_count.append('%' + keyword + '%')
        cursor.execute(count_sql, tuple(params_count))
        total = cursor.fetchone()['total']

        return {
          "list": results,
          'total': int(total),
          'current': int(page_num),
          'page_size': int(page_size),
        }
    except Exception as e:
      # 发生错误时打印错误信息
      print("发生错误：", e)
    finally:
      # 关闭数据库连接
      connect.close()