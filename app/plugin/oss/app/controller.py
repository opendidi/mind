'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-04-30 17:42:32
LastEditors: htang
LastEditTime: 2024-10-09 09:52:45
'''
# -*- coding: UTF-8 -*-

import oss2
import app.plugin.oss.config as config

auth = oss2.Auth(config.AccessKeyId, config.AccessKeySecret)
bucket = oss2.Bucket(auth, config.Endpoint, config.BucketName)

class OssUtil(object):

  '''
    # 要上传的本地文件名
    local_file = 'local_file.txt'
    # 上传后的文件名
    oss_file = 'remote_file.txt'
  '''
  def put_object_from_file(oss_path, file_path):
    bucket.put_object_from_file(oss_path, file_path)

  def oss_put_object(oss_path, file_object):
    bucket.put_object(oss_path, file_object)