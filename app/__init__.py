import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def create_app(test_config=None):
    app = Flask(__name__)

    data_dir = os.environ.get('DATA_DIR', os.path.join(os.getcwd(), 'data'))

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    db_path = os.path.join(data_dir, 'giftguardian.db')

    # Persist secret key across restarts (needed for flash messages to survive)
    secret_key_file = os.path.join(data_dir, '.secret_key')
    if os.path.exists(secret_key_file):
        with open(secret_key_file, 'rb') as f:
            secret_key = f.read()
    else:
        secret_key = os.urandom(24)
        with open(secret_key_file, 'wb') as f:
            f.write(secret_key)

    app.config['SECRET_KEY'] = secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(data_dir, 'images')

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)

    with app.app_context():
        from . import models
        db.create_all()

        # Migrate existing databases: add new columns if missing
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(gift)"))
            existing_cols = {row[1] for row in result}
            if 'image_url' not in existing_cols:
                conn.execute(text("ALTER TABLE gift ADD COLUMN image_url VARCHAR(500)"))
            if 'notes' not in existing_cols:
                conn.execute(text("ALTER TABLE gift ADD COLUMN notes TEXT"))
            conn.commit()

        from .routes import main
        app.register_blueprint(main)

    return app
