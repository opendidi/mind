'''
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2025-08-22 12:04:51
'''
from flask import Blueprint

from app.api.v1.categories import categories_api
from app.api.v1.material import material_api
from app.api.v1.blueprint import blueprint_api

def create_v1():
  bp_v1 = Blueprint("v1", __name__)
  bp_v1.register_blueprint(material_api, url_prefix = "/material")
  bp_v1.register_blueprint(categories_api, url_prefix = "/categories")
  bp_v1.register_blueprint(blueprint_api, url_prefix = "/blueprint")
  return bp_v1