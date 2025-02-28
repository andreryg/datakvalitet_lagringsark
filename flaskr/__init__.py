# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 11:56:33 2024

@author: andryg
"""

import os
from flask import Flask

def create_app(test_config = None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY = 'dev',
        DATABASE = os.path.join(app.instance_path, 'flaskr.sqlite')
        )
    
    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
    
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    @app.route('/hello')
    def hello():
        return 'Hello world!'
    
    from . import db
    db.init_app(app)
    
    from . import auth, views
    app.register_blueprint(auth.bp)
    app.register_blueprint(views.bp)
    app.add_url_rule('/', endpoint='index')
    
    return app