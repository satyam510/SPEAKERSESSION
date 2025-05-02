from datetime import datetime, timedelta
import json

from flask import Blueprint, jsonify, request, current_app, render_template
from flask_jwt_extended import (get_jwt_identity, jwt_required)

from app import db
from auth import (login_user, register_user, resend_otp, speaker_required,
                 user_required, verify_otp)
from calendar_service import create_mock_calendar_event
from models import Booking, SpeakerProfile, TimeSlot, User, UserType
from utils import (generate_available_time_slots, get_available_time_slots,
                  send_booking_confirmation_email)

# Main application routes
main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

# API routes
api = Blueprint('api', __name__, url_prefix='/api')

# Authentication Routes
@api.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    result, status_code = register_user(data)
    return jsonify(result), status_code

@api.route('/auth/verify-otp', methods=['POST'])
def verify():
    data = request.get_json()
    result, status_code = verify_otp(data)
    return jsonify(result), status_code

@api.route('/auth/resend-otp', methods=['POST'])
def resend():
    data = request.get_json()
    result, status_code = resend_otp(data)
    return jsonify(result), status_code

@api.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    result, status_code = login_user(data)
    return jsonify(result), status_code

@api.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    from auth import refresh_token
    result, status_code = refresh_token()
    return jsonify(result), status_code

# User Profile Routes
@api.route('/users/me', methods=['GET'])
@jwt_required()
def get_user_profile():
    current_user_id = get_jwt_identity().get('user_id')
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    user_data = user.to_dict()
    
    # If the user is a speaker, include speaker profile information
    if user.user_type == UserType.SPEAKER and user.speaker_profile:
        user_data['speaker_profile'] = user.speaker_profile.to_dict()
    
    return jsonify({
        'success': True,
        'user': user_data
    }), 200

@api.route('/users/me', methods=['PUT'])
@jwt_required()
def update_user_profile():
    current_user_id = get_jwt_identity().get('user_id')
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    data = request.get_json()
    
    try:
        # Update basic user information
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User profile updated successfully',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating user profile: {str(e)}'
        }), 500

# Speaker Profile Routes
@api.route('/speakers', methods=['GET'])
@jwt_required()
def get_speakers():
    # Get all users who are speakers and have verified accounts
    speakers = User.query.filter_by(user_type=UserType.SPEAKER).all()
    
    speaker_list = []
    for speaker in speakers:
        if speaker.speaker_profile:  # Only include speakers who have created profiles
            speaker_data = {
                'id': speaker.id,
                'first_name': speaker.first_name,
                'last_name': speaker.last_name,
                'email': speaker.email,
                'speaker_profile': speaker.speaker_profile.to_dict()
            }
            speaker_list.append(speaker_data)
    
    return jsonify({
        'success': True,
        'speakers': speaker_list
    }), 200

@api.route('/speakers/profile', methods=['POST', 'PUT'])
@jwt_required()
@speaker_required
def create_or_update_speaker_profile():
    current_user_id = get_jwt_identity().get('user_id')
    
    data = request.get_json()
    required_fields = ['expertise', 'price_per_session']
    
    # Validate required fields
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'message': f'Missing required field: {field}'
            }), 400
    
    try:
        # Check if profile already exists
        profile = SpeakerProfile.query.filter_by(user_id=current_user_id).first()
        
        if profile:
            # Update existing profile
            profile.expertise = data['expertise']
            profile.price_per_session = data['price_per_session']
            if 'bio' in data:
                profile.bio = data['bio']
        else:
            # Create new profile
            profile = SpeakerProfile(
                user_id=current_user_id,
                expertise=data['expertise'],
                price_per_session=data['price_per_session'],
                bio=data.get('bio', '')
            )
            db.session.add(profile)
        
        db.session.commit()
        
        # Generate time slots for the next 30 days
        today = datetime.now().date()
        generate_available_time_slots(current_user_id, today)
        
        return jsonify({
            'success': True,
            'message': 'Speaker profile updated successfully',
            'profile': profile.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating speaker profile: {str(e)}'
        }), 500

@api.route('/speakers/<int:speaker_id>', methods=['GET'])
@jwt_required()
def get_speaker_profile(speaker_id):
    user = User.query.get(speaker_id)
    
    if not user or user.user_type != UserType.SPEAKER:
        return jsonify({
            'success': False,
            'message': 'Speaker not found'
        }), 404
    
    if not user.speaker_profile:
        return jsonify({
            'success': False,
            'message': 'Speaker profile not found'
        }), 404
    
    # Get available time slots for the next 30 days
    today = datetime.now().date()
    end_date = today + timedelta(days=30)
    available_slots = get_available_time_slots(speaker_id, today, end_date)
    
    speaker_data = {
        'id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'speaker_profile': user.speaker_profile.to_dict(),
        'available_slots': available_slots
    }
    
    return jsonify({
        'success': True,
        'speaker': speaker_data
    }), 200

# Time Slot Management Routes
@api.route('/speakers/time-slots', methods=['GET'])
@jwt_required()
@speaker_required
def get_my_time_slots():
    current_user_id = get_jwt_identity().get('user_id')
    
    # Parse date parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = datetime.now().date()
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = start_date + timedelta(days=30)
        
        # Get time slots
        time_slots = TimeSlot.query.filter(
            TimeSlot.speaker_id == current_user_id,
            TimeSlot.date >= start_date,
            TimeSlot.date <= end_date
        ).order_by(TimeSlot.date, TimeSlot.hour).all()
        
        return jsonify({
            'success': True,
            'time_slots': [slot.to_dict() for slot in time_slots]
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving time slots: {str(e)}'
        }), 500

@api.route('/speakers/time-slots', methods=['POST'])
@jwt_required()
@speaker_required
def create_time_slots():
    current_user_id = get_jwt_identity().get('user_id')
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['start_date', 'end_date']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'message': f'Missing required field: {field}'
            }), 400
    
    try:
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        # Generate time slots
        slots = generate_available_time_slots(current_user_id, start_date, end_date)
        
        return jsonify({
            'success': True,
            'message': f'Created {len(slots)} time slots',
            'time_slots': [slot.to_dict() for slot in slots]
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating time slots: {str(e)}'
        }), 500

@api.route('/speakers/time-slots/<int:slot_id>', methods=['PUT'])
@jwt_required()
@speaker_required
def update_time_slot(slot_id):
    current_user_id = get_jwt_identity().get('user_id')
    
    # Find the time slot
    slot = TimeSlot.query.get(slot_id)
    
    if not slot:
        return jsonify({
            'success': False,
            'message': 'Time slot not found'
        }), 404
    
    # Verify ownership
    if slot.speaker_id != current_user_id:
        return jsonify({
            'success': False,
            'message': 'You do not have permission to update this time slot'
        }), 403
    
    # Check if the slot is already booked
    if slot.booking_id:
        return jsonify({
            'success': False,
            'message': 'Cannot update a booked time slot'
        }), 400
    
    data = request.get_json()
    
    try:
        if 'is_available' in data:
            slot.is_available = data['is_available']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Time slot updated successfully',
            'time_slot': slot.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating time slot: {str(e)}'
        }), 500

# Booking Routes
@api.route('/bookings', methods=['POST'])
@jwt_required()
@user_required
def create_booking():
    current_user_id = get_jwt_identity().get('user_id')
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['speaker_id', 'date', 'hour']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'message': f'Missing required field: {field}'
            }), 400
    
    speaker_id = data['speaker_id']
    date_str = data['date']
    hour = int(data['hour'])
    
    try:
        # Parse date
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Check if the time slot exists and is available
        time_slot = TimeSlot.query.filter_by(
            speaker_id=speaker_id,
            date=booking_date,
            hour=hour,
            is_available=True
        ).first()
        
        if not time_slot:
            return jsonify({
                'success': False,
                'message': 'Time slot not available or does not exist'
            }), 400
        
        # Create booking
        booking = Booking(
            user_id=current_user_id,
            speaker_id=speaker_id,
            booking_date=booking_date,
            start_time=hour,
            end_time=hour+1,
            status='confirmed'
        )
        db.session.add(booking)
        
        # Update time slot
        time_slot.is_available = False
        time_slot.booking_id = booking.id
        
        db.session.commit()
        
        # Create calendar event
        # For this sample, we'll use a mock calendar event
        event_id = create_mock_calendar_event(booking)
        
        if event_id:
            booking.calendar_event_id = event_id
            db.session.commit()
        
        # Send confirmation emails
        send_booking_confirmation_email(booking)
        
        return jsonify({
            'success': True,
            'message': 'Booking created successfully',
            'booking': booking.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Booking creation error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating booking: {str(e)}'
        }), 500

@api.route('/bookings/user', methods=['GET'])
@jwt_required()
def get_user_bookings():
    current_user_id = get_jwt_identity().get('user_id')
    user_type = get_jwt_identity().get('user_type')
    
    try:
        if user_type == UserType.USER.value:
            # Get bookings where the user is the client
            bookings = Booking.query.filter_by(user_id=current_user_id).all()
        elif user_type == UserType.SPEAKER.value:
            # Get bookings where the user is the speaker
            bookings = Booking.query.filter_by(speaker_id=current_user_id).all()
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid user type'
            }), 400
        
        return jsonify({
            'success': True,
            'bookings': [booking.to_dict() for booking in bookings]
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving bookings: {str(e)}'
        }), 500

@api.route('/bookings/<int:booking_id>', methods=['GET'])
@jwt_required()
def get_booking(booking_id):
    current_user_id = get_jwt_identity().get('user_id')
    
    booking = Booking.query.get(booking_id)
    
    if not booking:
        return jsonify({
            'success': False,
            'message': 'Booking not found'
        }), 404
    
    # Check authorization
    if booking.user_id != current_user_id and booking.speaker_id != current_user_id:
        return jsonify({
            'success': False,
            'message': 'You do not have permission to view this booking'
        }), 403
    
    return jsonify({
        'success': True,
        'booking': booking.to_dict()
    }), 200

@api.route('/bookings/<int:booking_id>', methods=['PUT'])
@jwt_required()
def update_booking_status(booking_id):
    current_user_id = get_jwt_identity().get('user_id')
    
    booking = Booking.query.get(booking_id)
    
    if not booking:
        return jsonify({
            'success': False,
            'message': 'Booking not found'
        }), 404
    
    # Check authorization (only the speaker can update the booking status)
    if booking.speaker_id != current_user_id:
        return jsonify({
            'success': False,
            'message': 'You do not have permission to update this booking'
        }), 403
    
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({
            'success': False,
            'message': 'Missing required field: status'
        }), 400
    
    valid_statuses = ['confirmed', 'cancelled', 'completed']
    if data['status'] not in valid_statuses:
        return jsonify({
            'success': False,
            'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
        }), 400
    
    try:
        booking.status = data['status']
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Booking status updated successfully',
            'booking': booking.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating booking status: {str(e)}'
        }), 500
