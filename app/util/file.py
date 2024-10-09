'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-04-22 15:31:45
LastEditors: htang
LastEditTime: 2024-10-09 08:57:35
'''
# -*- coding: UTF-8 -*-

import os
import re

def build_tree(materials):
  # 检查是否为空
  if not materials:
    return []

  # 创建材料字典
  material_dict = {m['id']: m for m in materials}

  # 初始化树结构
  tree = []

  for material in materials:
    if material['parent_id'] is None:  # 顶级目录
      # 为顶级目录添加 children 属性
      material['children'] = []
      tree.append(material)
    else:  # 子目录
      parent = material_dict.get(material['parent_id'])
      if parent:
        # 确保父节点的 children 数组存在
        if 'children' not in parent:
          parent['children'] = []
        parent['children'].append(material)

  return tree