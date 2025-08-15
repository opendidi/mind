'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2025-05-12 19:56:16
LastEditors: htang
LastEditTime: 2025-07-10 17:57:09
'''
import time
from typing import Any
from uuid import uuid4
from app.config.protocol import StatusCode, API_PROTOCOL

class ProtocolBuilder:

  @staticmethod
  def build_response(
    data: Any,
    code: StatusCode = StatusCode.SUCCESS,
    message: str = ""
  ) -> dict:
    """构造标准化响应协议"""
    return {
      "code": code.value,
      "data": data,
      "message": message,
      "request_id": str(uuid4()).replace("-", ""),
      "timestamp": int(time.time()),
      "version": API_PROTOCOL["current_version"].value
    }

  @staticmethod
  def validate_request(payload: dict) -> bool:
    """请求协议校验"""
    required_fields = ['signature', 'timestamp', 'nonce']
    return all(field in payload for field in required_fields)