# -*- coding: utf-8 -*-

from flask import jsonify

"""
 统一的json返回格式 (DEPRECATED — 请使用 ProtocolBuilder.build_response)
"""


class JsonResponse(object):

    def __init__(self, data, code, message):
        self.data = data
        self.code = code
        self.message = message

    @classmethod
    def success(cls, data=None, code=200, message="success"):
        return jsonify(cls(data, code, message).to_dict())

    @classmethod
    def error(cls, data=None, code=500, message="error"):
        return jsonify(cls(data, code, message).to_dict())

    def to_dict(self):
        return {"code": self.code, "message": self.message, "data": self.data}
