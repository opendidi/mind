'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2024-10-09 09:47:24
'''
# -*- coding: UTF-8 -*-

import logging
import pymysql
import pymysql.cursors
import os
from .connect import ConnectMysqlHandler
from app.util.log_config import setup_logging
from datetime import datetime
from app.plugin.minio.app.controller import MinioUtil
import app.plugin.minio.config as minio_conf
import app.util.file as PanoFile

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

  '''
    查询所有目录文件数据
  '''
  def foldertree(material_data):
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      params = []
      with connect.cursor() as cursor:
        sql = '''
          SELECT
            id, name, pano_id, url, file_path, thumb_path, type, size, extension,
            created_at,
            description,
            parent_id
          FROM
            material
          WHERE
            del = 0
          AND
            type = 'folder'
        '''
        cursor.execute(sql, tuple(params))
        results = cursor.fetchall()
        # 格式化时间
        for row in results:
          # 检查 created_at 的类型
          if isinstance(row['created_at'], str):
            row['created_at'] = datetime.strptime(row['created_at'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y-%m-%d %H:%M:%S')
          elif isinstance(row['created_at'], datetime):
            row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        return [dict(row) for row in results]
    except Exception as ex:
      logging.warning(ex)
    finally:
      connect.close()

  '''
    创建文件夹数据
    name: 文件夹名称
  '''
  def created_folder(material_data):
    name = material_data.get('name')
    parent_id = material_data.get('parent_id')
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = '''
          INSERT INTO `material` (`name`, `type`, `parent_id`) VALUES (%s, %s, %s)
        '''
        # 执行 SQL 语句
        cursor.execute(sql, (name, 'folder', parent_id))
        # 提交事务
        connect.commit()
    except Exception as ex:
      logging.warning(ex)
    finally:
      connect.close()

  def update_material(material_data):
    # 文件列表
    file_list = material_data.get('file_list')
    # 绝对路径
    root_path = material_data.get('root_path')
    # 文件类型
    file_type = material_data.get('file_type')
    # 父级id
    parent_id = material_data.get('parent_id')
    # 父级id
    timestamp = material_data.get('timestamp')
    # 用于存放每条插入记录的成功信息
    success_info = []
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        # 获取上传的文件
        for file in file_list:
          filename = file.filename
          if file and PanoFile.allowed_file(filename):
            # 把图片存储到临时目录
            file.save(os.path.join(root_path, filename))

            path = ''
            if platform == 'nt':
              path = root_path + '\\' + filename
            elif platform == 'posix':
              path = root_path + '/' + filename

            # 把全景图上传到阿里云
            oss_path = 'krpano/' + str(timestamp) + '/' + filename

            # minio 图片上传
            MinioUtil.upload_pano_file(path, oss_path)

            # 获取文件后缀
            file_name_with_extension = os.path.basename(path)

            file_name = os.path.splitext(file_name_with_extension)[0]

            # 获取文件后缀并去掉前面的点
            file_extension = os.path.splitext(path)[1][1:]

            name = file_name
            url = 'http://'+ minio_conf.minio_cdn_url + '/pano/' + oss_path
            pano_id = ''
            thumb_path = ''
            size = MinioUtil.get_object_size(oss_path)
            extension = file_extension

            # 收集成功信息
            success_info.append(f"Record {file_name} inserted successfully.")

            sql = """
              INSERT INTO `material` (`name`, `url`, `pano_id`, `thumb_path`, `size`, `extension`, `type`, `parent_id`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            # 执行 SQL 语句
            cursor.execute(sql, (name, url, pano_id, thumb_path, size, extension, file_type, parent_id))
        # 提交事务
        connect.commit()

        return success_info
    except Exception as ex:
      logging.warning(ex)
    finally:
      connect.close()

  '''
    url: 文件存储路径
    thumb_path: 全景图缩略图
    extension: 文件后缀
    pano_id: 全景图ID
  '''
  def install_material(material_data):
    url = material_data.get('url')
    pano_id = material_data.get('pano_id')
    thumb_path = material_data.get('thumb_path')
    size = material_data.get('size')
    extension = material_data.get('extension')
    material_type = material_data.get('type')
    name = os.path.basename(url)
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = """
          INSERT INTO `material` (`name`, `url`, `pano_id`, `thumb_path`, `size`, `extension`, `type`) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        # 执行 SQL 语句
        cursor.execute(sql, (name, url, pano_id, thumb_path, size, extension, material_type))
        # 提交事务
        connect.commit()
    except Exception as ex:
      logging.warning(ex)
    finally:
      connect.close()

  '''
    删除素材数据
  '''
  def delete_material(material_data):
    id = material_data.get('id')
    is_del = material_data.get('del')
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = """
          UPDATE `material` SET del = %s WHERE id = %s
        """
        # 执行 SQL 语句
        cursor.execute(sql, (is_del, id))
        # 提交事务
        connect.commit()
        return cursor.lastrowid
    except Exception as ex:
      logging.warning(ex)
    finally:
      connect.close()