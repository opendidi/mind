'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-09-19 09:34:03
LastEditors: htang
LastEditTime: 2024-09-19 09:34:12
'''
# -*- coding: UTF-8 -*-

import logging
import os

def setup_logging(
    log_file='app.log',
    level=logging.DEBUG,
    log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
):
  # 如果目录不存在，则创建目录
  log_directory = os.path.dirname(log_file)
  if not os.path.exists(log_directory):
    os.makedirs(log_directory)

  # 创建一个日志记录器，并设置其日志级别
  logger = logging.getLogger()
  logger.setLevel(level)

  # 创建一个文件处理器，并设置日志级别
  file_handler = logging.FileHandler(log_file)
  file_handler.setLevel(level)

  # 创建一个流处理器，以便也能在控制台打印日志
  stream_handler = logging.StreamHandler()
  stream_handler.setLevel(level)

  # 创建一个日志格式器，并设置到处理器上
  formatter = logging.Formatter(log_format)
  file_handler.setFormatter(formatter)
  stream_handler.setFormatter(formatter)

  # 为全局日志记录器添加处理器
  logger.addHandler(file_handler)
  logger.addHandler(stream_handler)

  return logger