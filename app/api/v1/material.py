'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-08-09 16:48:11
LastEditors: htang
LastEditTime: 2025-08-15 15:09:31
'''
from flask import Blueprint, Flask, render_template, request, Response, jsonify
from app.package.module.material_mysql import MaterialMysqlHandler
from app.util.file import build_tree
from app.util import contains_special_chars, generate_random_string
from app.plugin.minio.app.controller import MinioUtil
from app.util.protocol_handler import ProtocolBuilder
from app.config.protocol import StatusCode
import app.util.file as PanoFile
import time
import shutil
import os
import json

material_api = Blueprint("material", __name__)

# 获取操作系统类型
platform = os.name

@material_api.route("/lists", methods=['GET'])
def material_lists():
  current = request.args.get('current')
  size = request.args.get('page_size')
  keyword = request.args.get('keyword')
  folder = request.args.get('folder')
  parent_id = request.args.get('parent_id')
  sort_order = request.args.get('sort_order')
  type = request.args.get('type')
  data = MaterialMysqlHandler.query_list({
    'current': current,
    'page_size': size,
    'parent_id': parent_id,
    'sort_order': sort_order,
    'folder': folder,
    'keyword': keyword,
    'type': type,
  })
  return ProtocolBuilder.build_response(data)

@material_api.route("/preview", methods=['GET'])
def preview():
  id = request.args.get('id')
  result_data = MaterialMysqlHandler.find_material_by_id(id)
  data = {
    "name": '全景素材预览',
    "autorotate": False,
    "littleplanetintro": False,
    "gyro": False,
  }
  scene_group = []
  scene_group.append(json.loads(result_data['scene']))
  data['scene_group'] = scene_group
  return render_template('tour.xml', data = data)

'''
  获取文件管理器的目录
'''
@material_api.route("/folder", methods=['GET'])
def material_folder():
  data = MaterialMysqlHandler.foldertree()
  return ProtocolBuilder.build_response(build_tree(data), StatusCode.SUCCESS, '创建成功')

'''
  创建文件夹
'''
@material_api.route("/create_dir", methods=['POST'])
def create_dir():
  parent_id = request.form.get('parent_id')
  name = generate_random_string()
  # 检测特殊符号
  if contains_special_chars(name):
    # 返回400状态码表示错误
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '输入中包含不允许的字符：<>/\|"*?.')
  done = MaterialMysqlHandler.create_dir({
    "name": name,
    "parent_id": parent_id,
  })
  if done == None:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '新建失败')
  return ProtocolBuilder.build_response({}, StatusCode.SUCCESS, '新建成功')

'''
  上传文件到minio对象存储
'''
@material_api.route('/upload', methods=['POST'])
def upload_material():
  # 检查是否有文件被上传
  if 'file' not in request.files:
    response = {"code": 500, "msg": "No file found"}
    return jsonify(response)
  # 父级id
  parent_id = request.form.get("parent_id")
  # 全景图
  uploaded_files = request.files.getlist("file")
  # 是否有文件
  hisFile = request.files['file']

  if hisFile.filename == '':
    response = {"code": 415, "msg": "请选择素材文件"}
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
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '请选择要删除的数据')
  data = MaterialMysqlHandler.delete_material({
    'id': id,
    'del': 1
  })
  if data is not None:
    return ProtocolBuilder.build_response({}, StatusCode.SUCCESS, '删除成功')
  else:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '删除失败')

@material_api.route('/modify', methods=['POST'])
def material_modify():
  try:
    if request.content_type.startswith('multipart/form-data'):
      data = request.form.to_dict()
      id = data['id']
      if id == None or id == '':
        return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '请选择要修改的数据')
      name = data['name']
      bool = MaterialMysqlHandler.modify(id, name=name)
      if bool:
        return ProtocolBuilder.build_response({}, StatusCode.SUCCESS, '修改成功')
      else:
        return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '修改失败')
  except Exception as e:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, str(e))

@material_api.route('/scissors', methods=['POST'])
def scissors():
  try:
    if request.content_type.startswith('multipart/form-data'):
      data = request.form.to_dict()
      id = data['id']
      folder = data['folder']
      if id == None or id == '':
        return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '请选择要剪切的数据')
      done = MaterialMysqlHandler.scissors_file(id, folder)
      if done:
        return ProtocolBuilder.build_response({}, StatusCode.SUCCESS, '剪切成功')
      else:
        return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '剪切失败')
  except Exception as e:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, str(e))

@material_api.route('/copy', methods=['POST'])
def copy():
  try:
    if request.content_type.startswith('multipart/form-data'):
      data = request.form.to_dict()
      id = data['id']
      folder = data['folder']
      if id == None or id == '':
        return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '请选择要复制的数据')
      done = MaterialMysqlHandler.copy_file(id, folder)
      if done:
        return ProtocolBuilder.build_response({}, StatusCode.SUCCESS, '复制成功')
      else:
        return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '复制失败')
  except Exception as e:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, str(e))