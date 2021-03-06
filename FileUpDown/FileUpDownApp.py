#!/usr/bin/env python
# encoding: utf-8
"""
File UpDown Application Entry Point
This module is the entry point of the engine program, which will initialize
the environment and set up essential connection for other part of sub system.
Actually, it launches as a Flask application, for web service request handing.
"""
import os

from flask import Flask
# from werkzeug.contrib.fixers import ProxyFix

import GlobalConfigContext
from Gateway import FileGateway

app = Flask(__name__)
# app.wsgi_app = ProxyFix(app.wsgi_app)
app.register_blueprint(FileGateway.RestRouter)
app.config['SECRET_KEY'] = 'niang_pa_si'

if os.path.exists(GlobalConfigContext.FileStore_Directory) is not True:
    os.mkdir(GlobalConfigContext.FileStore_Directory)

if __name__ == '__main__':
    # app.debug = True
    app.run()
