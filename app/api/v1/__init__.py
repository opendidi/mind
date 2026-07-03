"""
Descripttion:
version: 1.0.0
Author: htang
Date: 2024-06-17 10:07:01
LastEditors: htang
LastEditTime: 2025-08-22 12:04:51
"""

from flask import Blueprint

from app.api.v1.agent import agent_api
from app.api.v1.auth import auth_api
from app.api.v1.blueprint import blueprint_api
from app.api.v1.categories import categories_api
from app.api.v1.chat import chat_api
from app.api.v1.material import material_api
from app.api.v1.translate import translate_api


def create_v1():
    bp_v1 = Blueprint("v1", __name__)
    bp_v1.register_blueprint(auth_api, url_prefix="/auth")
    bp_v1.register_blueprint(material_api, url_prefix="/material")
    bp_v1.register_blueprint(categories_api, url_prefix="/categories")
    bp_v1.register_blueprint(blueprint_api, url_prefix="/blueprint")
    bp_v1.register_blueprint(agent_api, url_prefix="/agent")
    bp_v1.register_blueprint(chat_api, url_prefix="/chat")
    bp_v1.register_blueprint(translate_api, url_prefix="/translate")
    return bp_v1
