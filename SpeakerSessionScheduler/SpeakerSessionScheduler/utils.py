import random
import string
from datetime import datetime, timedelta
from flask import render_template
from flask_mail import Message
from app import app, mail, db
from models import TimeSlot, User

def send_otp_email(email, otp_code):
    """Send OTP verification email to user."""
    msg = Message("Verify Your Speaker Session Account", recipients=[email])
    msg.html = render_template('email/otp_verification.html', otp_code=otp_code)
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Failed to send OTP email: {str(e)}")
        return False

def send_booking_confirmation_email(booking):
    """Send booking confirmation emails to both user and speaker."""
    # Get user and speaker details
    user = User.query.get(booking.user_id)
    speaker = User.query.get(booking.speaker_id)
    
    if not user or not speaker:
        app.logger.error(f"Failed to find user or speaker for booking: {booking.id}")
        return False
    
    # Prepare data for template
    booking_data = {
        'id': booking.id,
        'date': booking.booking_date.strftime('%A, %B %d, %Y'),
        'start_time': f"{booking.start_time}:00",
        'end_time': f"{booking.end_time}:00",
        'user_name': f"{user.first_name} {user.last_name}",
        'speaker_name': f"{speaker.first_name} {speaker.last_name}",
    }
    
    # Send email to user
    user_msg = Message(
        "Your Speaker Session Booking Confirmation", 
        recipients=[user.email]
    )
    user_msg.html = render_template(
        'email/booking_confirmation.html',
        recipient_type='user',
        booking=booking_data
    )
    
    # Send email to speaker
    speaker_msg = Message(
        "New Speaker Session Booking", 
        recipients=[speaker.email]
    )
    speaker_msg.html = render_template(
        'email/booking_confirmation.html',
        recipient_type='speaker',
        booking=booking_data
    )
    
    try:
        mail.send(user_msg)
        mail.send(speaker_msg)
        return True
    except Exception as e:
        app.logger.error(f"Failed to send booking confirmation emails: {str(e)}")
        return False

def generate_available_time_slots(speaker_id, start_date, end_date=None):
    """
    Generate available time slots for a speaker between start_date and end_date.
    If end_date is not provided, generate slots for 30 days from start_date.
    """
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    # Convert string dates to datetime if needed
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    business_hours_start = app.config.get('BUSINESS_HOURS_START', 9)  # 9 AM
    business_hours_end = app.config.get('BUSINESS_HOURS_END', 16)     # 4 PM
    
    current_date = start_date
    created_slots = []
    
    while current_date <= end_date:
        for hour in range(business_hours_start, business_hours_end):
            # Check if slot already exists
            existing_slot = TimeSlot.query.filter_by(
                speaker_id=speaker_id,
                date=current_date,
                hour=hour
            ).first()
            
            if not existing_slot:
                # Create new time slot
                new_slot = TimeSlot(
                    speaker_id=speaker_id,
                    date=current_date,
                    hour=hour,
                    is_available=True
                )
                db.session.add(new_slot)
                created_slots.append(new_slot)
        
        current_date += timedelta(days=1)
    
    if created_slots:
        db.session.commit()
    
    return created_slots

def get_available_time_slots(speaker_id, start_date, end_date=None):
    """Get available time slots for a speaker between start_date and end_date."""
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    # Convert string dates to datetime if needed
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Query available time slots
    available_slots = TimeSlot.query.filter(
        TimeSlot.speaker_id == speaker_id,
        TimeSlot.date >= start_date,
        TimeSlot.date <= end_date,
        TimeSlot.is_available == True
    ).order_by(TimeSlot.date, TimeSlot.hour).all()
    
    return [slot.to_dict() for slot in available_slots]

def format_time_slot(hour):
    """Format hour as a time string (e.g., 9 -> "9:00 AM")."""
    if hour < 12:
        return f"{hour}:00 AM"
    elif hour == 12:
        return "12:00 PM"
    else:
        return f"{hour-12}:00 PM"
