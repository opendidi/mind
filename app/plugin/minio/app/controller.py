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
      logging.error(f"MinIO stat_object error: {e}")
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

  @staticmethod
  def parse_source_prefix(url: str):
    """从物料 URL 解析 MinIO 源目录前缀（文件所在目录的 bucket-relative 路径）。

    URL 格式: http(s)://host:port/bucket/timestamp/filename.ext
    返回: timestamp/   （目录前缀，用于按 prefix 列出该目录下所有对象）
    对于旧格式 /pano/xxx/yy/ 也做兼容。
    """
    try:
      if not url:
        return None
      # 去掉协议和 host:port
      scheme_split = url.split("://", 1)[1] if "://" in url else url
      parts = scheme_split.split("/", 1)  # ["host:port", "bucket/timestamp/..."]
      if len(parts) < 2:
        return None
      # 去掉 bucket 名，保留目录部分
      bucket_and_rest = parts[1]
      path_parts = bucket_and_rest.split("/", 1)  # ["bucket", "timestamp/file.ext"]
      if len(path_parts) < 2:
        return None
      # 取文件所在目录 (去掉文件名)
      full_path = path_parts[1]  # "timestamp/file.ext" or "timestamp/sub/file.ext"
      dirname = '/'.join(full_path.split('/')[:-1])  # "timestamp" or "timestamp/sub"
      return dirname + '/' if dirname else ''
    except Exception:
      return None

  @staticmethod
  def copy_directory_prefix(source_prefix: str, target_prefix: str) -> bool:
    """复制 MinIO 中某个前缀下的所有对象到新前缀（保持目录结构）。

    用于全景图等包含多个附属文件（tile/配置）的目录复制。
    """
    try:
      from minio.commonconfig import CopySource
      objects = list(minio_client.list_objects(bucket_name, prefix=source_prefix, recursive=True))
      if not objects:
        logging.warning("copy_directory_prefix: 源前缀无对象: %s", source_prefix)
        return False

      for obj in objects:
        # 计算相对路径
        relative = obj.object_name[len(source_prefix):]  # 去掉源前缀
        target_object = target_prefix + relative
        copy_source = CopySource(bucket_name, obj.object_name)
        minio_client.copy_object(bucket_name, target_object, copy_source)

      logging.info("copy_directory_prefix: 复制了 %d 个对象 %s → %s",
                   len(objects), source_prefix, target_prefix)
      return True
    except Exception as e:
      logging.warning(f"copy_directory_prefix 失败: {source_prefix} → {target_prefix}: {e}")
      return False

  def find_source_path(file_name):
    try:
      objects = minio_client.list_objects(bucket_name, recursive=True)
      for obj in objects:
        if obj.object_name.endswith(file_name):
          return obj.object_name.replace(f'/{file_name}', '')
      logging.warning("find_source_path: 未找到匹配对象: %s", file_name)
      return ''
    except Exception as e:
      logging.warning(f"find_source_path error: {e}")
      return ''

  def copy_directory(file_name):
    try:
      timestamp = int(time.time())
      target_base = f'krpano/{timestamp}/'
      source_path = MinioUtil.find_source_path(file_name)
      if not source_path:
        logging.warning("copy_directory: find_source_path 返回空, file_name=%s", file_name)
        return ''

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