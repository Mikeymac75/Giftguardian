import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

def create_app(test_config=None):
    app = Flask(__name__)

    # Determine the data directory
    # In HA, this will be set to /data. Locally, we default to ./data
    data_dir = os.environ.get('DATA_DIR', os.path.join(os.getcwd(), 'data'))

    # Ensure data directory exists
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    db_path = os.path.join(data_dir, 'giftguardian.db')

    # Use a secure random key if not in dev mode (conceptually), or just generate one at runtime
    # Since this is an HA addon, sessions are less critical for auth (handled by HA),
    # but needed for flash messages.
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(data_dir, 'images')

    # Ensure upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)

    with app.app_context():
        from . import models
        db.create_all()

        from .routes import main
        app.register_blueprint(main)

    from .middleware import IngressMiddleware
    app.wsgi_app = IngressMiddleware(app.wsgi_app)

    return app
