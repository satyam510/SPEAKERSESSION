import random
import string
from datetime import datetime, timedelta
from functools import wraps

from flask import jsonify, request
from flask_jwt_extended import (create_access_token, create_refresh_token,
                               get_jwt_identity, jwt_required)
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, jwt
from models import OTP, User, UserType, VerificationStatus
from utils import send_otp_email


def generate_otp(length=6):
    """Generate a random numeric OTP of specified length."""
    return ''.join(random.choices(string.digits, k=length))


def register_user(data):
    """Register a new user."""
    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return {
            'success': False,
            'message': 'User with this email already exists.'
        }, 409

    # Create new user
    try:
        user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            password=data['password'],
            user_type=UserType(data['user_type'])
        )
        db.session.add(user)
        db.session.commit()

        # Generate and send OTP for email verification
        otp_code = generate_otp()
        otp = OTP(
            user_id=user.id,
            otp_code=otp_code
        )
        db.session.add(otp)
        db.session.commit()

        # Send OTP email
        send_otp_email(user.email, otp_code)

        return {
            'success': True,
            'message': 'User registered successfully. Please verify your email with the OTP sent.',
            'user_id': user.id
        }, 201
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'Error registering user: {str(e)}'
        }, 500


def verify_otp(data):
    """Verify OTP for a user."""
    user_id = data.get('user_id')
    otp_code = data.get('otp_code')

    # Find the user
    user = User.query.get(user_id)
    if not user:
        return {
            'success': False,
            'message': 'User not found'
        }, 404

    # Check if user is already verified
    if user.verification_status == VerificationStatus.VERIFIED:
        return {
            'success': False,
            'message': 'User is already verified'
        }, 400

    # Find the latest valid OTP for the user
    otp = OTP.query.filter_by(
        user_id=user_id,
        otp_code=otp_code
    ).order_by(OTP.created_at.desc()).first()

    if not otp:
        return {
            'success': False,
            'message': 'Invalid OTP'
        }, 400

    if otp.is_expired():
        return {
            'success': False,
            'message': 'OTP has expired'
        }, 400

    # Mark user as verified
    try:
        user.verification_status = VerificationStatus.VERIFIED
        db.session.commit()

        return {
            'success': True,
            'message': 'OTP verified successfully. Your account is now active.'
        }, 200
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'Error verifying OTP: {str(e)}'
        }, 500


def resend_otp(data):
    """Resend OTP for user verification."""
    email = data.get('email')

    # Find the user
    user = User.query.filter_by(email=email).first()
    if not user:
        return {
            'success': False,
            'message': 'User not found'
        }, 404

    # Check if user is already verified
    if user.verification_status == VerificationStatus.VERIFIED:
        return {
            'success': False,
            'message': 'User is already verified'
        }, 400

    # Generate and send new OTP
    try:
        otp_code = generate_otp()
        otp = OTP(
            user_id=user.id,
            otp_code=otp_code
        )
        db.session.add(otp)
        db.session.commit()

        # Send OTP email
        send_otp_email(user.email, otp_code)

        return {
            'success': True,
            'message': 'OTP sent successfully',
            'user_id': user.id
        }, 200
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'Error sending OTP: {str(e)}'
        }, 500


def login_user(data):
    """Login a user and generate JWT tokens."""
    email = data.get('email')
    password = data.get('password')

    # Find the user
    user = User.query.filter_by(email=email).first()
    if not user:
        return {
            'success': False,
            'message': 'Invalid email or password'
        }, 401

    # Check password
    if not user.check_password(password):
        return {
            'success': False,
            'message': 'Invalid email or password'
        }, 401

    # Check if user is verified
    if user.verification_status != VerificationStatus.VERIFIED:
        return {
            'success': False,
            'message': 'Account not verified. Please verify your email first.'
        }, 403

    # Generate tokens
    access_token = create_access_token(identity={
        'user_id': user.id,
        'email': user.email,
        'user_type': user.user_type.value
    })
    refresh_token = create_refresh_token(identity={
        'user_id': user.id,
        'email': user.email,
        'user_type': user.user_type.value
    })

    return {
        'success': True,
        'message': 'Login successful',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'user_type': user.user_type.value
        }
    }, 200


@jwt.user_identity_loader
def user_identity_lookup(user):
    """Convert user identity to a JSON serializable format."""
    if isinstance(user, dict):
        return user
    return {'user_id': user.id, 'email': user.email, 'user_type': user.user_type.value}


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    """Load user from database based on JWT claims."""
    identity = jwt_data["sub"]
    if isinstance(identity, dict):
        user_id = identity.get('user_id')
    else:
        user_id = identity
    return User.query.get(user_id)


def speaker_required(fn):
    """Custom decorator to check if user has speaker role."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        if not current_user or current_user.get('user_type') != UserType.SPEAKER.value:
            return jsonify(message="Speaker access required"), 403
        return fn(*args, **kwargs)
    return wrapper


def user_required(fn):
    """Custom decorator to check if user has user role."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        if not current_user or current_user.get('user_type') != UserType.USER.value:
            return jsonify(message="User access required"), 403
        return fn(*args, **kwargs)
    return wrapper


def refresh_token():
    """Refresh the user's access token."""
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return {
        'success': True,
        'access_token': access_token
    }, 200
