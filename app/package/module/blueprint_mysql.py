'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2025-08-22 14:03:29
LastEditors: htang
LastEditTime: 2025-08-26 15:20:22
'''
# -*- coding: UTF-8 -*-

import logging
import pymysql
import pymysql.cursors
import os
import json
import uuid
import app.util.file as PanoFile
from .connect import ConnectMysqlHandler
from app.util.log_config import setup_logging
from datetime import datetime
from app.plugin.minio.app.controller import MinioUtil
from app.plugin.minio import minio_cdn_url

dirname = os.path.dirname(os.path.abspath(__name__))

class BlueprintMysqlHandler:

  def query_list(params, user_id):
    page_num = params['current']
    page_size = params['page_size']
    keyword = params['keyword']
    data = []
    connect = None
    try:
      offset = (int(page_num) - 1) * int(page_size)
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        params = [user_id]
        sql = "SELECT id, name, color, penBackground, background, bkImage, grid, gridColor, gridSize, gridRotate, rule, ruleColor, initJs, pens, https, thumbnail, created_at FROM blueprint WHERE del = 0 AND user_id = %s "
        if keyword:
          sql += "AND name LIKE %s "
          params.append('%' + keyword + '%')
        sql += "ORDER BY created_at DESC LIMIT {} OFFSET {}".format(page_size, offset)
        cursor.execute(sql, tuple(params))
        results = cursor.fetchall()

        for row in results:
          if isinstance(row['created_at'], str):
            row['created_at'] = datetime.strptime(row['created_at'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y-%m-%d %H:%M:%S')
          elif isinstance(row['created_at'], datetime):
            row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        params_count = [user_id]
        count_sql = '''
          SELECT COUNT(*) as total FROM blueprint WHERE del = 0 AND user_id = %s
        '''
        if keyword:
          count_sql += "AND name LIKE %s "
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
      print(f"发生错误：{e}")
    finally:
      if connect:
          connect.close()

  def find(id, user_id):
    if not id:
      logging.warning("ID 不能为空")
      return False
    connect = None
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = ''' select id, name, color, penBackground, background, bkImage, grid, gridColor, gridSize, gridRotate, rule, ruleColor, initJs, pens, https, thumbnail from blueprint where id = %s and del = 0 and user_id = %s '''
        cursor.execute(sql, (id, user_id))
        result = cursor.fetchone()
        if result is None:
          return False
        if result['initJs']:
          result['initJs'] = json.loads(result['initJs'])
        if result['https']:
          result['https'] = json.loads(result['https'])
        if result['pens']:
          result['pens'] = json.loads(result['pens'])
        return result
    except Exception as e:
      print(f"发生错误：{e}")
    finally:
      if connect:
          connect.close()

  def add(data, user_id):
    id = str(uuid.uuid4()).replace("-", "")
    name = data.get('name')
    color = data.get('color')
    penBackground = data.get('penBackground')
    background = data.get('background')
    bkImage = data.get('bkImage')
    grid = data.get('grid')
    gridColor = data.get('gridColor')
    gridSize = data.get('gridSize')
    gridRotate = data.get('gridRotate')
    rule = data.get('rule')
    ruleColor = data.get('ruleColor')
    initJs = data.get('initJs')
    pens = data.get('pens')
    https = data.get('https')
    thumbnail = data.get('thumbnail')
    connect = None
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = "INSERT INTO blueprint (id, name, color, penBackground, background, bkImage, grid, gridColor, gridSize, gridRotate, rule, ruleColor, initJs, pens, https, thumbnail, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (id, name, color, penBackground, background, bkImage, grid, gridColor, gridSize, gridRotate, rule, ruleColor, initJs, pens, https, thumbnail, user_id))
        connect.commit()
        if cursor.rowcount == 0:
          return False, "数据增加失败"
        return True, id
    except Exception as e:
      print(f"发生错误：{e}")
      return False, str(e)
    finally:
      if connect:
          connect.close()

  def modify(id, user_id, **kwargs):
    if not id:
      logging.warning("ID 不能为空")
      return False
    connect = None
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        for key in kwargs:
          if isinstance(kwargs[key], dict):
            kwargs[key] = json.dumps(kwargs[key], ensure_ascii=False)
        update_fields = [f"{key} = %s" for key in kwargs.keys()]
        values = list(kwargs.values())

        sql = f"UPDATE blueprint SET {', '.join(update_fields)} WHERE id = %s AND user_id = %s"
        values.append(id)
        values.append(user_id)

        cursor.execute(sql, values)
        connect.commit()

        if cursor.rowcount == 0:
          return False, "未找到匹配的 ID 或数据未变更"
        return True, cursor.rowcount
    except Exception as ex:
      logging.warning(f"数据增加失败：{ex}")
    finally:
      if connect:
          connect.close()

  '''
    删除图纸
  '''
  def delete_blueprint(params, user_id):
    id = params.get('id')
    is_del = params.get('del')
    connect = None
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = """
          UPDATE `blueprint` SET del = %s WHERE id = %s AND user_id = %s
        """
        cursor.execute(sql, (is_del, id, user_id))
        connect.commit()
        return cursor.lastrowid
    except Exception as ex:
      logging.warning(ex)
    finally:
      if connect:
          connect.close()
