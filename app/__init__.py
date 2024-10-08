# -*- coding: UTF-8 -*-

from flask import Flask
from flask_cors import CORS

def register_blueprints(app):
  from app.api.v1 import create_v1
  app.register_blueprint(create_v1(), url_prefix = "/v1")

def create_app():
  app = Flask(__name__, static_folder='static', static_url_path='/v1/static')
  CORS(app)
  register_blueprints(app)

  return app