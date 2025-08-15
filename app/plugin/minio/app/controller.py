'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2025-06-27 11:21:43
'''
import logging
from minio import Minio
from minio.error import S3Error
from app.plugin.minio import minio_bucket_name, minio_endpoint, minio_cdn_url, minio_access_key, minio_secret_key, minio_secure
import os
import time
from minio.commonconfig import CopySource

bucket_name = minio_bucket_name

# 获取当前文件所在路径（确保无论从哪运行都能找到 app/static）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_PANOS_DIR = os.path.join(BASE_DIR, 'app', 'static', 'panos')

minio_client = Minio(
  endpoint = minio_endpoint,
  access_key = minio_access_key,
  secret_key = minio_secret_key,
  secure = minio_secure
)

class MinioUtil:
  # 列出所有存储桶
  def list_buckets():
    buckets = minio_client.list_buckets()
    for bucket in buckets:
      logging.info(bucket.name)

  # 上传文件到存储桶
  def upload_pano_file(file_path, object_name):
    try:
      # 使用 put_object 方法上传文件
      minio_client.fput_object(bucket_name, object_name, file_path)
      return 'http://' + minio_cdn_url + '/' + bucket_name + '/' + object_name
    except Exception as e:
      logging.warning(f"Error: {e}")
      return ''

  def get_object_size(object_name):
    try:
      # 获取对象的元数据
      stat = minio_client.stat_object(bucket_name, object_name)
      # 返回对象的大小
      return stat.size
    except S3Error as e:
      print(f"Error occurred: {e}")
      return None

  def download_minio_folder(minio_paths, root):
    for path in minio_paths:
      # 去掉 bucket 前缀后计算相对路径
      rel_path = "/".join(path.split("/")[3:])
      timestamp = "/".join(path.split("/")[2:3])

      prefix = path[len(f"pano/"):]

      # 2. 列出所有对象（包括子文件夹）
      objects = minio_client.list_objects(bucket_name, prefix=prefix, recursive=True)

      for obj in objects:
        object_name = obj.object_name
        # 原图通常为 krpano/时间戳/文件.jpeg（路径深度 = 2）
        if object_name.endswith('.jpeg') and object_name.count('/') == 2:
          continue  # 过滤掉原图
        rel_path = os.path.join("panos", object_name[len(f"krpano/{timestamp}/"):])
        target_path = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        # 下载到本地
        minio_client.fget_object(bucket_name, object_name, target_path)

  def find_source_path(file_name):
    try:
      # 查找文件
      objects = minio_client.list_objects(bucket_name, recursive=True)
      source_path = None
      for obj in objects:
        if obj.object_name.endswith(file_name):
          source_path = obj.object_name.replace(f'/{file_name}', '')
          break
      return source_path
    except Exception as e:
      logging.warning(f"Error: {e}")
      return ''

  def copy_directory(file_name):
    try:
      timestamp = int(time.time())
      target_base = f'krpano/{timestamp}/'
      # 源目录
      source_path = MinioUtil.find_source_path(file_name)

      path_parts = source_path.rstrip('/').split('/')
      depth = len(path_parts)

      # 列出所有对象
      objects = minio_client.list_objects(bucket_name, prefix=source_path, recursive=True)

      for obj in objects:
        parts = obj.object_name.split('/')

        # 获取源路径之后的部分
        relative_parts = parts[depth-0:]
        new_path = target_base + '/'.join(relative_parts)

        # 执行复制
        copy_source = CopySource(bucket_name, obj.object_name)
        minio_client.copy_object(bucket_name, new_path, copy_source)

      return target_base
    except Exception as e:
      logging.warning(f"Error: {e}")
      return ''