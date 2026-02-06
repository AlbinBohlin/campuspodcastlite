from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)          # e.g. "The Daily Tech", "Albin's Music Corner"
    description = db.Column(db.Text, nullable=True)
    creator_name = db.Column(db.String(100), nullable=True)   # optional: host name, band name, etc.
    cover_image_path = db.Column(db.String(200), nullable=True)  # optional future
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_name': self.creator_name
        }

# Database Model
class Episode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(200), nullable=False)

    collection_id = db.Column(db.Integer, db.ForeignKey(Collection.id), nullable=False)
    collection = db.relationship('Collection', backref='episodes', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'file_path': self.file_path,
            'collection_id': self.collection_id,
            'collection_name': self.collection.name if self.collection else None
        }
    
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # never store plain passwords!
    role = db.Column(db.String(20), default='user')           # optional: user / admin / creator
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role
        }
    
