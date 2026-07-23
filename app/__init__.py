import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__, template_folder='../templates')
    app.config.from_object(config[config_name])

    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.auth.routes import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.main.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # ADD THESE LINES HERE
    from app.models import User, Download

    with app.app_context():
        db.create_all()

    return app