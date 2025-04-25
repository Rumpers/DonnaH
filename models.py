from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Text

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    telegram_id = db.Column(db.String(64), unique=True)
    google_credentials = db.Column(Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
    memory_entries = db.relationship('MemoryEntry', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy='dynamic')
    
    def __repr__(self):
        return f'<Conversation {self.id}>'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_user = db.Column(db.Boolean, default=True)  # True if from user, False if from bot
    
    def __repr__(self):
        return f'<Message {self.id}>'

class MemoryEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    entry_type = db.Column(db.String(64))  # 'project', 'person', 'event', etc.
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text)
    meta_data = db.Column(JSON)  # Renamed from metadata as it's a reserved name
    vector_embedding = db.Column(db.Text)  # For vector-based search
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MemoryEntry {self.id}: {self.title}>'

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    drive_id = db.Column(db.String(256))  # Google Drive file ID
    title = db.Column(db.String(256))
    file_type = db.Column(db.String(64))
    content_text = db.Column(db.Text)  # Extracted text content if applicable
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    memory_id = db.Column(db.Integer, db.ForeignKey('memory_entry.id'))
    memory = db.relationship('MemoryEntry', backref='documents')
    
    def __repr__(self):
        return f'<Document {self.id}: {self.title}>'
