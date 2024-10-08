'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2024-09-25 11:23:14
'''
# -*- coding: UTF-8 -*-

import re

# 定义过滤函数
def contains_special_chars(data):
  # 定义要过滤的符号
  return bool(re.search(r'[<>\/\\|:"*?.]', data))