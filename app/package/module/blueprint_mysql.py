'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2025-08-22 14:03:29
LastEditors: htang
LastEditTime: 2025-08-22 15:08:29
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

  def query_list(params):
    page_num = params['current']
    page_size = params['page_size']
    keyword = params['keyword']
    data = []
    try:
      # 计算起始记录的偏移量
      offset = (int(page_num) - 1) * int(page_size)
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = "SELECT id, name, color, penBackground, background, bkImage, grid, gridColor, gridSize, gridRotate, rule, ruleColor, initJs, pens, https FROM blueprint WHERE del = 0 "
        sql += "LIMIT {} OFFSET {}".format(page_size, offset)
        print(sql)
        cursor.execute(sql, tuple(data))
        results = cursor.fetchall()

        params_count = []

        count_sql = '''
          SELECT COUNT(*) as total FROM blueprint WHERE del = 0
        '''
        if keyword is not None:
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
      # 发生错误时打印错误信息
      print(f"发生错误：{e}")
    finally:
      # 关闭数据库连接
      connect.close()

  def find(id):
    if not id:
      logging.warning("ID 不能为空")
      return False
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = ''' select id, name, color, penBackground, background, bkImage, grid, gridColor, gridSize, gridRotate, rule, ruleColor, initJs, pens, https from blueprint where id = %s and del = 0 '''
        cursor.execute(sql, (id,))
        result = cursor.fetchone()
        if result is None:
          return False
        result['initJs'] = json.loads(result['initJs'])
        result['pens'] = json.loads(result['pens'])
        return result
    except Exception as e:
      # 发生错误时打印错误信息
      print(f"发生错误：{e}")
    finally:
      connect.close()

  def add(data):
    id = str(uuid.uuid4()).replace("-", "")
    name = data['name']
    color = data['color']
    penBackground = data['penBackground']
    background = data['background']
    bkImage = data['bkImage']
    grid = data['grid']
    gridColor = data['gridColor']
    gridSize = data['gridSize']
    gridRotate = data['gridRotate']
    rule = data['rule']
    ruleColor = data['ruleColor']
    initJs = data['initJs']
    pens = data['pens']
    https = data['https']
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = "INSERT INTO blueprint (id, name, color, penBackground, background, bkImage, grid, gridColor, gridSize, gridRotate, rule, ruleColor, initJs, pens, https) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (id, name, color, penBackground, background, bkImage, grid, gridColor, gridSize, gridRotate, rule, ruleColor, initJs, pens, https))
        connect.commit()
        if cursor.rowcount == 0:
          return False, "数据增加失败"
        return True
    except Exception as e:
      # 发生错误时打印错误信息
      print(f"发生错误：{e}")
    finally:
      connect.close()

  def modify(id, **kwargs):
    if not id:
      logging.warning("ID 不能为空")
      return False
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        for key in kwargs:
          # 如果值是字典
          if isinstance(kwargs[key], dict):
            # 转成 JSON 字符串
            kwargs[key] = json.dumps(kwargs[key], ensure_ascii=False)
        update_fields = [f"{key} = %s" for key in kwargs.keys()]
        values = list(kwargs.values())

        sql = f"UPDATE blueprint SET {', '.join(update_fields)} WHERE id = %s"
        values.append(id)

        cursor.execute(sql, values)
        connect.commit()

        if cursor.rowcount == 0:
          return False, "未找到匹配的 ID 或数据未变更"
        return True, cursor.rowcount
    except Exception as ex:
      logging.warning(f"数据增加失败：{ex}")
    finally:
      connect.close()

  '''
    删除图纸
  '''
  def delete_blueprint(params):
    id = params.get('id')
    is_del = params.get('del')
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = """
          UPDATE `blueprint` SET del = %s WHERE id = %s
        """
        cursor.execute(sql, (is_del, id))
        connect.commit()
        return cursor.lastrowid
    except Exception as ex:
      logging.warning(ex)
    finally:
      connect.close()