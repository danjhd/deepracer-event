import logging
import os
from logging.handlers import RotatingFileHandler
from flask import Flask, request
from aws_xray_sdk.core import patch_all, xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
from config import Config
from flask_babel import Babel
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.config.from_object(Config)
bootstrap = Bootstrap(app)
babel = Babel(app)
xray_recorder.configure(service='flask-app', plugins=('ElasticBeanstalkPlugin', 'EC2Plugin', 'ECSPlugin'))
XRayMiddleware(app, xray_recorder)
patch_all()

if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/flask-app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Flask App startup')

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(app.config['LANGUAGES'])

from app import errors, routes
