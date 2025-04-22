from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base

# Set up database
Base = declarative_base()
db = SQLAlchemy(model_class=Base)

def init_db(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)
