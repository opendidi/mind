'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2025-08-15 10:45:00
'''
# -*- coding: UTF-8 -*-

import re
import secrets
import string

# 定义过滤函数
def contains_special_chars(data):
  # 定义要过滤的符号
  return bool(re.search(r'[<>\/\\|:"*?.]', data))

def generate_random_string(length=13):
  characters = string.ascii_letters + string.digits
  return ''.join(secrets.choice(characters) for _ in range(length))

def extract_after_krpano(full_path):
  match = re.search(r'krpano/\d+/(.+)', full_path)
  return f"panos/{match.group(1)}" if match else full_path