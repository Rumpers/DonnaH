from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Text, UniqueConstraint
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)  # Changed to string for Replit Auth sub
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # May be null for some auth methods
    password_hash = db.Column(db.String(256), nullable=True)  # Optional for OAuth
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    telegram_id = db.Column(db.String(64), unique=True, nullable=True)
    google_credentials = db.Column(Text, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)  # Admin flag for user management
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# OAuth model for Replit Auth
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

# Add relationships to User model
User.conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
User.memory_entries = db.relationship('MemoryEntry', backref='user', lazy='dynamic')

# Add __repr__ method to User class
User.__repr__ = lambda self: f'<User {self.username}>'

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
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
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    entry_type = db.Column(db.String(64))  # 'project', 'person', 'event', etc.
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text)
    meta_data = db.Column(JSON)  # Renamed from metadata as it's a reserved name
    vector_embedding = db.Column(db.Text)  # For vector-based search
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    face_images = db.relationship('FaceImage', backref='memory_entry', lazy='dynamic')
    
    def __repr__(self):
        return f'<MemoryEntry {self.id}: {self.title}>'

class FaceImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    memory_entry_id = db.Column(db.Integer, db.ForeignKey('memory_entry.id'), nullable=False)
    image_path = db.Column(db.String(512))  # Path to stored image
    image_url = db.Column(db.String(512))   # URL if from web search
    is_profile = db.Column(db.Boolean, default=False)  # True if primary profile image
    face_encoding = db.Column(db.Text)  # Facial feature encoding for recognition
    source = db.Column(db.String(64))  # 'upload', 'business_card', 'web_search'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FaceImage {self.id} for {self.memory_entry_id}>'

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
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
