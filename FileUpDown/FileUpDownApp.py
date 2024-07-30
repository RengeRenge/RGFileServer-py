#!/usr/bin/env python
# encoding: utf-8
"""
File UpDown Application Entry Point
This module is the entry point of the engine program, which will initialize
the environment and set up essential connection for other part of sub system.
Actually, it launches as a Flask application, for web service request handing.
"""
import logging
import os

from flask import Flask
# from werkzeug.contrib.fixers import ProxyFix

import GlobalConfigContext
from Gateway import FileGateway

os.makedirs(GlobalConfigContext.FileStore_Directory, exist_ok=True)
app = Flask(__name__)
# app.wsgi_app = ProxyFix(app.wsgi_app)
app.register_blueprint(FileGateway.RestRouter)
app.config["SECRET_KEY"] = "niang_pa_si"

# handler
handler = logging.StreamHandler()
formater = logging.Formatter(
    fmt="[%(asctime)s] [%(thread)s] [%(levelname)s] [%(filename)s:%(lineno)d] [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S %z",
)

handler.setFormatter(formater)
handler.setLevel(logging.WARN)

# logger
logger = logging.getLogger('file')

logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

app.logger = logger

if __name__ == "__main__":
    app.debug = True
    if app.debug:
        handler.setLevel(logging.DEBUG)
    app.run()
