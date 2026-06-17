'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-09-03 10:56:14
LastEditors: htang
LastEditTime: 2024-10-08 21:12:59
'''
# -*- coding: UTF-8 -*-

from .connect import ConnectMysqlHandler

class CategoriesMysqlHandler:

  def query_list(user_id):
    connect = None
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = """
          SELECT
            id, name, description, sort_order,
            DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_time, status
          FROM
            categories
          WHERE
            user_id = %s
          ORDER BY
            sort_order
          DESC
        """
        cursor.execute(sql, (user_id,))
        result = cursor.fetchall()
        return result
    except Exception as e:
      print("发生错误：", e)
    finally:
      if connect:
          connect.close()
