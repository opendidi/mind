'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2025-08-15 16:15:00
'''
# -*- coding: UTF-8 -*-

import logging
import pymysql
import pymysql.cursors
import os
import json
import uuid
import app.util.file as PanoFile
from pathlib import Path
from .connect import ConnectMysqlHandler
from app.util.log_config import setup_logging
from datetime import datetime
from app.plugin.minio.app.controller import MinioUtil
from app.plugin.minio import minio_cdn_url

dirname = os.path.dirname(os.path.abspath(__name__))

# 获取操作系统类型
platform = os.name

if platform == 'nt':
  logger = setup_logging(log_file= dirname + '\\app\\log\\MaterialMysqlHandler.log')

def extract_path_segment(url, start_segment="/pano/", levels=2):
  # 分割路径部分
  path = url.split(start_segment)[1]
  # 再次分割获取所需部分
  result = "/".join(path.split("/")[:levels])
  return result + '/'

class MaterialMysqlHandler:

  def query_list(material_data):
    page_num = material_data.get('current')
    page_size = material_data.get('page_size')
    keyword = material_data.get('keyword')
    type = material_data.get('type')
    folder = material_data.get('folder')
    parent_id = material_data.get('parent_id')
    sort_order = material_data.get('sort_order')
    params = []
    try:
      # 计算起始记录的偏移量
      offset = (int(page_num) - 1) * int(page_size)
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = """
          SELECT
            id, name, url, file_path, thumb_path, size, extension,
            created_at, description, parent_id, type, `lock`
          FROM
            material
          WHERE
            del = 0
        """
        if type is not None:
          sql += "AND type = %s "
          params.append(type)
        if folder is not None:
          sql += "AND name = %s "
          params.append(folder)
        if parent_id is not None:
          sql += "AND parent_id = %s "
          params.append(parent_id)
        if keyword is not None:
          sql += "AND name LIKE %s "
          params.append('%' + keyword + '%')
        # 添加动态排序
        if sort_order is not None:
          # 防止SQL注入，只允许特定排序方向
          order = 'DESC' if sort_order.upper() == 'DESC' else 'ASC'
          # 默认排序
          sql += f"ORDER BY created_at {order} "
        else:
          # 如果没有指定排序方向，默认降序
          sql += "ORDER BY created_at DESC "
        sql += "LIMIT {} OFFSET {}".format(page_size, offset)
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
        if parent_id is not None:
          count_sql += "AND parent_id = %s "
          params_count.append(parent_id)
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

  def find_material_by_id(id):
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = '''
          SELECT
            id, name, url, file_path, thumb_path, size, extension,
            created_at,
            description,
            parent_id,
            type,
            `lock`,
            `path`
          FROM
            material
          WHERE
            id = %s and del = 0
        '''
        cursor.execute(sql, (id,))
        # 获取所有记录列表
        return cursor.fetchone()
    except Exception as ex:
      logging.warning(ex)
    finally:
      connect.close()

  '''
    查询所有目录文件数据
  '''
  def foldertree():
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      params = []
      with connect.cursor() as cursor:
        sql = '''
          SELECT
            id, name, url, file_path, thumb_path, type, size, extension,
            created_at,
            description,
            parent_id,
            `lock`,
            `path`
          FROM
            material
          WHERE
            del = 0
          AND
            type = 'dir'
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
        print(results)
        return [dict(row) for row in results]
    except Exception as ex:
      logging.warning(ex)
    finally:
      connect.close()

  '''
    创建文件夹数据
    name: 文件夹名称
  '''
  def create_dir(material_data):
    try:
      id = str(uuid.uuid4()).replace("-", "")
      name = material_data.get('name')
      parent_id = material_data.get('parent_id')
      path = name # 默认路径为当前目录名
      if parent_id:
        parent = MaterialMysqlHandler.find_material_by_id(parent_id)
        if parent and parent.get('path'):
          path = f"{parent['path']}/{material_data['name']}"
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = '''
          INSERT INTO `material` (`id`, `name`, `type`, `parent_id`, `path`) VALUES (%s, %s, %s, %s, %s)
        '''
        # 执行 SQL 语句
        print(id)
        cursor.execute(sql, (id, name, 'dir', parent_id, path))
        # 提交事务
        connect.commit()
        return True
    except Exception as ex:
      logging.warning(ex)
      return False
    finally:
      connect.close()

  def update_material(material_data):
    id = str(uuid.uuid4()).replace("-", "")
    # 文件列表
    file_list = material_data.get('file_list')
    # 绝对路径
    root_path = material_data.get('root_path')
    # 父级id
    parent_id = material_data.get('parent_id', 0)
    # 时间戳
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
            oss_path = str(timestamp) + '/' + filename

            file_type = Path(path).suffix

            MinioUtil.upload_pano_file(path, oss_path)

            # 获取文件后缀
            file_name_with_extension = os.path.basename(path)

            file_name = os.path.splitext(file_name_with_extension)[0]

            # 获取文件后缀并去掉前面的点
            file_extension = os.path.splitext(path)[1][1:]

            name = file_name
            url = f'http://{minio_cdn_url}/pano/{oss_path}'
            thumb_path = ''
            size = MinioUtil.get_object_size(oss_path)
            extension = file_extension

            sql = """
              INSERT INTO `material` (`id`, `name`, `url`, `thumb_path`, `size`, `extension`, `type`, `parent_id`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            # 执行 SQL 语句
            cursor.execute(sql, (id, name, url, thumb_path, size, extension, file_type, parent_id))

            # 收集成功信息
            success_info.append(cursor.lastrowid)
            # 提交事务
            connect.commit()

        return success_info
    except Exception as ex:
      logging.warning(ex)
      return None
    finally:
      connect.close()

  '''
    url: 文件存储路径
    thumb_path: 全景图缩略图
    extension: 文件后缀
  '''
  def install_material(material_data):
    id = str(uuid.uuid4()).replace("-", "")
    url = material_data.get('url')
    thumb_path = material_data.get('thumb_path')
    size = material_data.get('size')
    extension = material_data.get('extension')
    type = material_data.get('type')
    parent_id = material_data.get('parent_id')
    name = os.path.basename(url)
    try:
      connect = ConnectMysqlHandler.connect_mysql()
      with connect.cursor() as cursor:
        sql = """
          INSERT INTO `material` (`id`, `name`, `url`, `thumb_path`, `size`, `extension`, `type`, `parent_id`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (id, name, url, thumb_path, size, extension, type, parent_id))
        connect.commit()
        return cursor.rowcount
    except Exception as ex:
      logging.warning(ex)
      return False
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
        cursor.execute(sql, (is_del, id))
        connect.commit()
        return cursor.lastrowid
    except Exception as ex:
      logging.warning(ex)
    finally:
      connect.close()

  def modify(id, **kwargs):
    if not id:
      logging.warning("ID 不能为空")
      return False
    if not kwargs:
      logging.warning("没有可更新的字段")
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

        sql = f"UPDATE material SET {', '.join(update_fields)} WHERE id = %s"
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

  def scissors_file(id, folder = None):
    done = MaterialMysqlHandler.copy_file(id, folder)
    if done:
      MaterialMysqlHandler.delete_material({'id' : id, 'del' : 1})
      return True
    else:
      return False

  def copy_file(id, folder = None):
    try:
      # 根据ID查询文件信息
      info = MaterialMysqlHandler.find_material_by_id(id)

      # 获取文件名
      file_name = info['name']
      connect = ConnectMysqlHandler.connect_mysql()
      # 临时路径段
      before_temp_path = extract_path_segment(info['url'])

      # 开始复制文件
      after_path = MinioUtil.copy_directory(file_name)

      if after_path:
        data = {
          'name': file_name,
          'url': info['url'].replace(f'{before_temp_path}', after_path),
          'thumb_path': info['thumb_path'].replace(f'{before_temp_path}', after_path),
          'size': MinioUtil.get_object_size(after_path + file_name),
          'extension': os.path.splitext(file_name)[1][1:],
          'type': 'panorama',
          'parent_id': folder,
        }
        done = MaterialMysqlHandler.install_material(data)
        if done:
          return True
      else:
        return False
    except Exception as ex:
      logging.warning(ex)
      return False
    finally:
      connect.close()