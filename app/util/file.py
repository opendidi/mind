'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-04-22 15:31:45
LastEditors: htang
LastEditTime: 2025-08-15 17:53:45
'''
# -*- coding: UTF-8 -*-

import os
import re

# 设置允许的文件类型
ALLOWED_EXTENSIONS = { 'png', 'jpg', 'jpeg', 'mp3', 'mp4', 'gif', 'txt', 'doc', 'avi', 'css', 'csv', 'dbf', 'dwg', 'exe', 'fla', 'flash', 'html', 'iso', 'javascript', 'json', 'pdf', 'ppt', 'psd', 'rtf', 'svg', 'xls', 'xml', 'zip'
}

# html js swf xml JPG
delete_file_name = ['tour.html', 'tour.js', 'tour.swf', 'tour.xml']

def allowed_file(filename):
  return '.' in filename and \
    filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def delete_folder(path):
  if os.path.exists(path):
    for filename in os.listdir(path):
      file_path = os.path.join(path, filename)
      if os.path.isfile(file_path):
        os.remove(file_path)
    os.rmdir(path)

def delete_file(path):
  if os.path.exists(path):
    os.remove(path)

# 匹配JPG PNT JPEG 替换为空字符
def replace_extension(path):
  return re.sub(r'\.JPG$|\.PNT$|\.JPEG$', '', path)

# 正则表达式匹配文件名（假设文件名没有特殊字符）
# 这里使用了正则表达式的零宽断言，(?<=\\) 表示前面是反斜杠，但不包含在匹配结果中
# [^\\]+ 表示匹配一个或多个非反斜杠字符，\.\w+ 表示匹配点和后面的文件扩展名
def replaced_string(path):
  pattern = r'(?<=\\)[^\\]+\.\w+$'
  # 替换文件名为一个空字符串
  return re.sub(pattern, '', path)

def build_tree(items, parent_id=None):
  """
  递归构建树形结构
  :param items: 所有项目的列表
  :param parent_id: 当前父节点ID
  :return: 树形结构列表
  """
  tree = []
  for item in items:
    if item['parent_id'] == parent_id:
      node = {
        'id': item['id'],
        'name': item['name'],
        'type': item['type'],
        'path': item['path'],
        'created_at': item['created_at'],
        'children': build_tree(items, item['id'])  # 递归查找子节点
      }
      tree.append(node)
  return tree