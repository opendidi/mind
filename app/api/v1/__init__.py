'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2024-10-08 21:24:45
'''
from flask import Blueprint

from app.api.v1.categories import categories_api
from app.api.v1.material import material_api

def create_v1():
  bp_v1 = Blueprint("v1", __name__)
  bp_v1.register_blueprint(material_api, url_prefix = "/material")
  bp_v1.register_blueprint(categories_api, url_prefix = "/categories")
  return bp_v1