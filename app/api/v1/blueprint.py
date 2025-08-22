# -*- coding: UTF-8 -*-

from flask import Blueprint, Flask, render_template, request, Response, jsonify
from app.util.file import build_tree
from app.package.module.blueprint_mysql import BlueprintMysqlHandler
from app.util import contains_special_chars, generate_random_string
from app.plugin.minio.app.controller import MinioUtil
from app.util.protocol_handler import ProtocolBuilder
from app.config.protocol import StatusCode
import app.util.file as PanoFile
import json

blueprint_api = Blueprint("blueprint", __name__)

@blueprint_api.route("/lists", methods=['GET'])
def blueprint_lists():
  current = request.args.get('current')
  size = request.args.get('page_size')
  keyword = request.args.get('keyword')
  data = BlueprintMysqlHandler.query_list({
    'current': current,
    'page_size': size,
    'keyword': keyword,
  })
  return ProtocolBuilder.build_response(data)

@blueprint_api.route("/find", methods=['GET'])
def find():
  id = request.args.get('id')
  if id == None or id == '':
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, 'ID不能为空')
  data = BlueprintMysqlHandler.find(id)
  return ProtocolBuilder.build_response(data)

@blueprint_api.route("/add", methods=['POST'])
def add():
  try:
    if request.content_type.startswith('multipart/form-data'):
      data = request.form.to_dict()
      if contains_special_chars(data['name']):
        return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '名称不能包含特殊字符')
      if data['name'] == None or data['name'] == '':
        return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '名称不能为空')
      ok, id = BlueprintMysqlHandler.add({
        'name': data['name'],
        'color': data['color'],
        'penBackground': data['penBackground'],
        'background': data['background'],
        'bkImage': data['bkImage'],
        'grid': data['grid'],
        'gridColor': data['gridColor'],
        'gridSize': data['gridSize'],
        'gridRotate': data['gridRotate'],
        'rule': data['rule'],
        'ruleColor': data['ruleColor'],
        'initJs': data['initJs'],
        'pens': data['pens'],
        'https': data['https'],
        'thumbnail': data['thumbnail'],
      })
      if ok:
        return ProtocolBuilder.build_response({'id': id}, StatusCode.SUCCESS, '添加成功')
      else:
        return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '添加失败')
  except Exception as e:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, str(e))

@blueprint_api.route("/modify", methods=['POST'])
def modify():
  try:
    if request.content_type.startswith('multipart/form-data'):
      data = request.form.to_dict()
      id = data['id']
      if id == None or id == '':
        return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, 'ID不能为空')
  except Exception as e:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, str(e))

'''
  删除图纸
'''
@blueprint_api.route('/delete', methods=['POST'])
def delete_blueprint():
  # 文件类型
  id = request.form.get("id")
  if id == None or id == '':
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '请选择要删除的数据')
  data = BlueprintMysqlHandler.delete_blueprint({
    'id': id,
    'del': 1
  })
  if data is not None:
    return ProtocolBuilder.build_response({}, StatusCode.SUCCESS, '删除成功')
  else:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '删除失败')