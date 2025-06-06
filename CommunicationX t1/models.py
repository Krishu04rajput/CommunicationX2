from datetime import datetime
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    username = db.Column(db.String(64), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='online')  # online, away, busy, invisible
    location = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), default='member')  # admin, moderator, member
    permissions = db.Column(db.JSON, nullable=True)  # Custom permissions JSON
    last_active = db.Column(db.DateTime, default=datetime.now)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    owned_servers = db.relationship('Server', backref='owner', lazy=True)
    messages = db.relationship('Message', backref='author', lazy=True)
    direct_messages_sent = db.relationship('DirectMessage', foreign_keys='DirectMessage.sender_id', backref='sender', lazy=True)
    direct_messages_received = db.relationship('DirectMessage', foreign_keys='DirectMessage.recipient_id', backref='recipient', lazy=True)

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
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

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String, nullable=True)
    owner_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    is_public = db.Column(db.Boolean, default=True)  # Public servers auto-add all users
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    channels = db.relationship('Channel', backref='server', lazy=True, cascade='all, delete-orphan')
    memberships = db.relationship('ServerMembership', backref='server', lazy=True, cascade='all, delete-orphan')

class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    messages = db.relationship('Message', backref='channel', lazy=True, cascade='all, delete-orphan')

class ServerMembership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref='server_memberships')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False, index=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    edited_at = db.Column(db.DateTime, nullable=True)
    message_type = db.Column(db.String(20), default='text')  # text, file, image, video
    file_url = db.Column(db.String, nullable=True)  # For file attachments
    file_name = db.Column(db.String, nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)
    
    # Self-referential relationship for replies
    reply_to = db.relationship('Message', remote_side=[id], backref='replies')

class DirectMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False, index=True)
    recipient_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    audio_data = db.Column(db.Text, nullable=True)  # Base64 encoded audio data
    reply_to_id = db.Column(db.Integer, db.ForeignKey('direct_message.id'), nullable=True)
    
    # Self-referential relationship for replies
    reply_to = db.relationship('DirectMessage', remote_side=[id], backref='replies')

class Call(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caller_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True)  # For server calls
    call_type = db.Column(db.String(10), nullable=False)  # 'audio' or 'video'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'active', 'ended', 'declined'
    started_at = db.Column(db.DateTime, default=datetime.now)
    ended_at = db.Column(db.DateTime, nullable=True)
    voicemail_url = db.Column(db.String, nullable=True)  # For voicemail recordings
    
    # Relationships
    caller = db.relationship('User', foreign_keys=[caller_id], backref='calls_made')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='calls_received')
    server = db.relationship('Server', backref='server_calls')

class CallMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(db.Integer, db.ForeignKey('call.id'), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    call = db.relationship('Call', backref='call_messages')
    user = db.relationship('User', backref='call_messages')

class SharedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    uploader_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    uploader = db.relationship('User', backref='uploaded_files')
    server = db.relationship('Server', backref='shared_files')
    channel = db.relationship('Channel', backref='shared_files')

class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    inviter_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    uses_left = db.Column(db.Integer, default=1)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    inviter = db.relationship('User', backref='invitations_sent')

class Voicemail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    audio_url = db.Column(db.String, nullable=False)
    duration = db.Column(db.Integer, nullable=True)  # in seconds
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='voicemails_sent')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='voicemails_received')
