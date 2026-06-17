# -*- coding: UTF-8 -*-

from flask import Blueprint, Flask, render_template, request, Response, jsonify, g
from app.package.module.blueprint_mysql import BlueprintMysqlHandler
from app.util import contains_special_chars
from app.plugin.minio.app.controller import MinioUtil
from app.util.protocol_handler import ProtocolBuilder
from app.config.protocol import StatusCode
from app.util.decorators import token_required

blueprint_api = Blueprint("blueprint", __name__)

@blueprint_api.route("/lists", methods=['GET'])
@token_required
def blueprint_lists():
  current = request.args.get('current')
  size = request.args.get('page_size')
  keyword = request.args.get('keyword')
  data = BlueprintMysqlHandler.query_list({
    'current': current,
    'page_size': size,
    'keyword': keyword,
  }, g.user_id)
  return ProtocolBuilder.build_response(data)

@blueprint_api.route("/find", methods=['GET'])
@token_required
def find():
  id = request.args.get('id')
  if id == None or id == '':
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, 'ID不能为空')
  data = BlueprintMysqlHandler.find(id, g.user_id)
  return ProtocolBuilder.build_response(data)

@blueprint_api.route("/add", methods=['POST'])
@token_required
def add():
  try:
    if request.is_json:
      data = request.get_json(silent=True) or {}
    elif request.content_type and request.content_type.startswith('multipart/form-data'):
      data = request.form.to_dict()
    else:
      return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '不支持的 Content-Type，请使用 JSON 或 form-data')

    name = data.get('name', '').strip() if isinstance(data.get('name'), str) else ''
    if not name:
      return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '名称不能为空')
    if contains_special_chars(name):
      return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '名称不能包含特殊字符')

    ok, id = BlueprintMysqlHandler.add({
      'name': name,
      'color': data.get('color', ''),
      'penBackground': data.get('penBackground', ''),
      'background': data.get('background', ''),
      'bkImage': data.get('bkImage', ''),
      'grid': data.get('grid', ''),
      'gridColor': data.get('gridColor', ''),
      'gridSize': data.get('gridSize', ''),
      'gridRotate': data.get('gridRotate', ''),
      'rule': data.get('rule', ''),
      'ruleColor': data.get('ruleColor', ''),
      'initJs': data.get('initJs', ''),
      'pens': data.get('pens', ''),
      'https': data.get('https', ''),
      'thumbnail': data.get('thumbnail', ''),
    }, g.user_id)
    if ok:
      return ProtocolBuilder.build_response({'id': id}, StatusCode.SUCCESS, '添加成功')
    else:
      return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, f'添加失败: {id}')
  except Exception as e:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, str(e))

@blueprint_api.route("/modify", methods=['POST'])
@token_required
def modify():
  try:
    if request.is_json:
      data = request.get_json(silent=True) or {}
    elif request.content_type and request.content_type.startswith('multipart/form-data'):
      data = request.form.to_dict()
    else:
      return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '不支持的 Content-Type，请使用 JSON 或 form-data')

    id = data.get('id', '')
    if not id:
      return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, 'ID不能为空')
    ok = BlueprintMysqlHandler.modify(id, g.user_id, **{
      'name': data.get('name', ''),
      'color': data.get('color', ''),
      'penBackground': data.get('penBackground', ''),
      'background': data.get('background', ''),
      'bkImage': data.get('bkImage', ''),
      'grid': data.get('grid', ''),
      'gridColor': data.get('gridColor', ''),
      'gridSize': data.get('gridSize', ''),
      'gridRotate': data.get('gridRotate', ''),
      'rule': data.get('rule', ''),
      'ruleColor': data.get('ruleColor', ''),
      'initJs': data.get('initJs', ''),
      'pens': data.get('pens', ''),
      'https': data.get('https', ''),
      'thumbnail': data.get('thumbnail', ''),
    })
    if ok:
      return ProtocolBuilder.build_response({}, StatusCode.SUCCESS, '修改成功')
    else:
      return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '修改失败')
  except Exception as e:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, str(e))

'''
  删除图纸
'''
@blueprint_api.route('/delete', methods=['POST'])
@token_required
def delete_blueprint():
  if request.is_json:
    data = request.get_json(silent=True) or {}
  else:
    data = request.form
  id = data.get("id", "").strip() if isinstance(data.get("id"), str) else ""
  if not id:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '请选择要删除的数据')
  data = BlueprintMysqlHandler.delete_blueprint({
    'id': id,
    'del': 1
  }, g.user_id)
  if data is not None:
    return ProtocolBuilder.build_response({}, StatusCode.SUCCESS, '删除成功')
  else:
    return ProtocolBuilder.build_response({}, StatusCode.INTERNAL_ERROR, '删除失败')
