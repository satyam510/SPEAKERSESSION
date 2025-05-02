from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import enum
import uuid

class UserType(enum.Enum):
    USER = "user"
    SPEAKER = "speaker"

class VerificationStatus(enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    user_type = db.Column(db.Enum(UserType), nullable=False)
    verification_status = db.Column(db.Enum(VerificationStatus), default=VerificationStatus.PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    speaker_profile = db.relationship('SpeakerProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    bookings_as_user = db.relationship('Booking', foreign_keys='Booking.user_id', backref='user', lazy=True)
    sessions_as_speaker = db.relationship('Booking', foreign_keys='Booking.speaker_id', backref='speaker', lazy=True)

    def __init__(self, first_name, last_name, email, password, user_type):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.set_password(password)
        self.user_type = user_type
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'user_type': self.user_type.value,
            'verification_status': self.verification_status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class OTP(db.Model):
    __tablename__ = 'otps'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('otps', lazy=True))
    
    def __init__(self, user_id, otp_code, expiry_minutes=10):
        self.user_id = user_id
        self.otp_code = otp_code
        self.expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

class SpeakerProfile(db.Model):
    __tablename__ = 'speaker_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    expertise = db.Column(db.String(500), nullable=False)
    price_per_session = db.Column(db.Float, nullable=False)
    bio = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'expertise': self.expertise,
            'price_per_session': self.price_per_session,
            'bio': self.bio,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'email': self.user.email,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    speaker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Integer, nullable=False)  # Store hour as integer (9 for 9 AM, 14 for 2 PM)
    end_time = db.Column(db.Integer, nullable=False)    # Store hour as integer
    status = db.Column(db.String(20), default='confirmed')
    calendar_event_id = db.Column(db.String(255), nullable=True)  # Google Calendar event ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': f"{self.user.first_name} {self.user.last_name}",
            'user_email': self.user.email,
            'speaker_id': self.speaker_id,
            'speaker_name': f"{self.speaker.first_name} {self.speaker.last_name}",
            'speaker_email': self.speaker.email,
            'booking_date': self.booking_date.isoformat(),
            'start_time': self.start_time,
            'end_time': self.end_time,
            'status': self.status,
            'calendar_event_id': self.calendar_event_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class TimeSlot(db.Model):
    __tablename__ = 'time_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    speaker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hour = db.Column(db.Integer, nullable=False)  # Store hour as integer (9 for 9 AM, 14 for 2 PM)
    is_available = db.Column(db.Boolean, default=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    speaker = db.relationship('User', backref=db.backref('time_slots', lazy=True))
    booking = db.relationship('Booking', backref=db.backref('time_slot', lazy=True), uselist=False)
    
    __table_args__ = (
        db.UniqueConstraint('speaker_id', 'date', 'hour', name='unique_time_slot'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'speaker_id': self.speaker_id,
            'date': self.date.isoformat(),
            'hour': self.hour,
            'is_available': self.is_available,
            'booking_id': self.booking_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
