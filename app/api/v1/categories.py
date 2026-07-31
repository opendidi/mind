# -*- coding: UTF-8 -*-

from flask import Blueprint, Flask, Response, g, jsonify, render_template, request

from app.package.module.categories_mysql import CategoriesMysqlHandler
from app.util.decorators import token_required

categories_api = Blueprint("categories", __name__)


@categories_api.route("/lists", methods=["GET"])
@token_required
def categories_lists():
    data = CategoriesMysqlHandler.query_list(g.user_id)
    response = {"code": 200, "message": "success", "data": data}
    return jsonify(response)
