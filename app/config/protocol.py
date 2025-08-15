'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2025-05-12 19:55:36
LastEditors: htang
LastEditTime: 2025-05-12 19:55:50
'''
# -*- coding: UTF-8 -*-

"""
API通信协议标准定义
"""
from enum import Enum

class ProtocolVersion(str, Enum):
  V1 = "1.0"
  V2 = "2.0"

class StatusCode(Enum):
  SUCCESS = 200
  BAD_REQUEST = 400
  UNAUTHORIZED = 401
  INTERNAL_ERROR = 500
  # 403 错误码
  FORBIDDEN = 403

API_PROTOCOL = {
  "current_version": ProtocolVersion.V2,
  "response_template": {
      "code": StatusCode.SUCCESS,
      "data": None,
      "message": "",
      "request_id": "",
      "timestamp": 0
  },
  "signature_required": True
}