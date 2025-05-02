import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
jwt = JWTManager()
mail = Mail()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the app
app.config.from_object('config.Config')

# Initialize CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize extensions with app
db.init_app(app)
jwt.init_app(app)
mail.init_app(app)

# Create database tables
with app.app_context():
    # Import models here to avoid circular imports
    import models  # noqa: F401

    db.create_all()
    logger.debug("Database tables created")
