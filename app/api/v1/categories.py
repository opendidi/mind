# -*- coding: UTF-8 -*-

from flask import Blueprint, g, Flask, render_template, request, Response, jsonify
from app.package.module.categories_mysql import CategoriesMysqlHandler

categories_api = Blueprint("categories", __name__)

@categories_api.route("/lists", methods=['GET'])
def categories_lists():
  data = CategoriesMysqlHandler.query_list()
  response = {"code": 200, "msg": "success", "data": data}
  return jsonify(response)