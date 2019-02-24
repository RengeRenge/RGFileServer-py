#!/usr/bin/env python
# encoding: utf-8
"""
File UpDown Application Entry Point
This module is the entry point of the engine program, which will initialize
the environment and set up essential connection for other part of sub system.
Actually, it launches as a Flask application, for web service request handing.
"""
from flask import Flask
from Gateway import FileGateway
from werkzeug.contrib.fixers import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.register_blueprint(FileGateway.RestRouter)
app.config['SECRET_KEY'] = 'niang_pa_si'


if __name__ == '__main__':
    app.debug = True
    app.run()
