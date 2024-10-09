'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2024-09-19 14:39:34
'''
import logging
from minio import Minio
from minio.error import S3Error

import app.plugin.minio.config as config

bucket_name = config.minio_bucket_name

minio_client = Minio(
  endpoint = config.minio_endpoint,
  access_key = config.minio_access_key,
  secret_key = config.minio_secret_key,
  secure = config.minio_secure
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
      return 'http://' + config.minio_cdn_url + '/' + bucket_name + '/' + object_name
    except Exception as e:
      logging.warning("Error:", e)
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