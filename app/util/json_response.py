# -*- coding: utf-8 -*-

from flask import make_response, jsonify

"""
 统一的json返回格式
"""
class JsonResponse(object):

  def __init__(self, data, code, msg):
    self.data = data
    self.code = code
    self.msg = msg

  @classmethod
  def success(cls, data = None, code = 1, msg = 'success'):
    return jsonify(cls(data, code, msg).to_dict())

  @classmethod
  def error(cls, data = None, code = -1, msg = 'error'):
    jsonify(cls(data, code, msg).to_dict())

  def to_dict(self):
    return { "code": self.code, "msg": self.msg, "data": self.data }