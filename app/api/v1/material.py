'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-08-09 16:48:11
LastEditors: htang
LastEditTime: 2024-09-26 17:56:38
'''
from flask import Blueprint, Flask, render_template, request, Response, jsonify
from app.package.module.material_mysql import MaterialMysqlHandler
from app.util.file import build_tree
from app.util import contains_special_chars
import app.util.file as PanoFile
import app.plugin.minio.config as minio_conf
from app.plugin.minio.app.controller import MinioUtil
import time
import shutil
import os

material_api = Blueprint("material", __name__)

# 获取操作系统类型
platform = os.name

@material_api.route("/lists", methods=['GET'])
def material_lists():
  current = request.args.get('current')
  size = request.args.get('page_size')
  type = request.args.get('type')
  keyword = request.args.get('keyword')
  parent_id = request.args.get('parent_id')
  data = MaterialMysqlHandler.query_list({
    'current': current,
    'page_size': size,
    'material_type': type,
    'parent_id': parent_id,
    'keyword': keyword,
  })
  return jsonify({"code": 200, "msg": "success", "data": data})

'''
  获取文件管理器的目录
'''
@material_api.route("/folder", methods=['GET'])
def material_folder():
  data = MaterialMysqlHandler.foldertree({})
  return jsonify({"code": 200, "msg": "success", "data": build_tree(data)})

'''
  创建文件夹
'''
@material_api.route("/created_folder", methods=['POST'])
def created_folder():
  name = request.form.get('name')
  parent_id = request.form.get('parent_id')
  if name == '' or name == None:
    return jsonify({"code": 415, "msg": "请输入文件夹名称", "data": None})
  # 检测特殊符号
  if contains_special_chars(name):
    # 返回400状态码表示错误
    return jsonify({'code': 500, 'msg': '输入中包含不允许的字符：<>/\|"*?.'})
  data = MaterialMysqlHandler.created_folder({
    "name": name,
    "parent_id": parent_id,
  })
  return jsonify({"code": 200, "msg": "新建成功", "data": data})

'''
  上传文件到minio对象存储
'''
@material_api.route('/upload', methods=['POST'])
def upload_material():
  # 检查是否有文件被上传
  if 'file' not in request.files:
    response = {"code": 500, "msg": "No file found", "data": None}
    return jsonify(response)

  # 文件类型
  file_type = request.form.get("type")

  # 父级id
  parent_id = request.form.get("parent_id")

  # 全景图
  uploaded_files = request.files.getlist("file")

  hisFile = request.files['file']

  if hisFile.filename == '':
    response = {"code": 415, "msg": "请选择素材文件", "data": None}
    return jsonify(response)

  localFile = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'static', 'images')

  timestamp = int(time.time())

  root_path = ''
  if platform == 'nt':
    root_path = localFile + '\\' + str(timestamp)
  elif platform == 'posix':
    root_path = localFile + '/' + str(timestamp)

  if not os.path.exists(root_path):
    os.makedirs(root_path)

  # 用于存放每条插入记录的成功信息
  success_info = MaterialMysqlHandler.update_material({
    'file_list': uploaded_files,
    'root_path': root_path,
    'file_type': file_type,
    'parent_id': parent_id,
    'timestamp': timestamp,
  })
  # 删除临时文件夹
  shutil.rmtree(root_path)
  if success_info == None:
    response = {"code": 500, "msg": "上传失败"}
  else:
    response = {"code": 200, "msg": "上传成功", "data": success_info}
  return jsonify(response)

'''
  上传文件到minio对象存储
'''
@material_api.route('/delete', methods=['POST'])
def delete_material():
  # 文件类型
  id = request.form.get("id")
  if id == None or id == '':
    return jsonify({"code": 500, "msg": "请选择要删除的数据"})
  data = MaterialMysqlHandler.delete_material({
    'id': id,
    # 默认写死
    'del': 1
  })
  if data is not None:
    return jsonify({"code": 200, "msg": "删除成功"})
  else:
    return jsonify({"code": 500, "msg": "删除失败"})