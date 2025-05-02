from flask import Blueprint
from flask_restx import Api, Resource, fields, Namespace

# Create Blueprint for Swagger docs
swagger_blueprint = Blueprint('swagger', __name__, url_prefix='/api/docs')

# Create API
api = Api(swagger_blueprint, version='1.0', title='Speaker Session Booking API',
          description='API for booking speaker sessions',
          doc='/swagger')

# Create namespaces
auth_ns = api.namespace('auth', description='Authentication operations')
users_ns = api.namespace('users', description='User operations')
speakers_ns = api.namespace('speakers', description='Speaker operations')
bookings_ns = api.namespace('bookings', description='Booking operations')

# Models for request and response validation
# Authentication models
registration_model = api.model('Registration', {
    'first_name': fields.String(required=True, description='First name'),
    'last_name': fields.String(required=True, description='Last name'),
    'email': fields.String(required=True, description='Email address'),
    'password': fields.String(required=True, description='Password'),
    'user_type': fields.String(required=True, description='User type (user or speaker)')
})

otp_verification_model = api.model('OTPVerification', {
    'user_id': fields.Integer(required=True, description='User ID'),
    'otp_code': fields.String(required=True, description='OTP code')
})

resend_otp_model = api.model('ResendOTP', {
    'email': fields.String(required=True, description='Email address')
})

login_model = api.model('Login', {
    'email': fields.String(required=True, description='Email address'),
    'password': fields.String(required=True, description='Password')
})

token_model = api.model('Token', {
    'access_token': fields.String(description='JWT access token'),
    'refresh_token': fields.String(description='JWT refresh token')
})

# User models
user_model = api.model('User', {
    'id': fields.Integer(description='User ID'),
    'first_name': fields.String(description='First name'),
    'last_name': fields.String(description='Last name'),
    'email': fields.String(description='Email address'),
    'user_type': fields.String(description='User type'),
    'verification_status': fields.String(description='Account verification status')
})

user_update_model = api.model('UserUpdate', {
    'first_name': fields.String(description='First name'),
    'last_name': fields.String(description='Last name')
})

# Speaker models
speaker_profile_model = api.model('SpeakerProfile', {
    'expertise': fields.String(required=True, description='Speaker expertise'),
    'price_per_session': fields.Float(required=True, description='Price per session'),
    'bio': fields.String(description='Speaker bio')
})

time_slot_model = api.model('TimeSlot', {
    'id': fields.Integer(description='Time slot ID'),
    'speaker_id': fields.Integer(description='Speaker ID'),
    'date': fields.Date(description='Date'),
    'hour': fields.Integer(description='Hour'),
    'is_available': fields.Boolean(description='Availability status')
})

time_slot_create_model = api.model('TimeSlotCreate', {
    'start_date': fields.String(required=True, description='Start date (YYYY-MM-DD)'),
    'end_date': fields.String(required=True, description='End date (YYYY-MM-DD)')
})

time_slot_update_model = api.model('TimeSlotUpdate', {
    'is_available': fields.Boolean(required=True, description='Availability status')
})

# Booking models
booking_create_model = api.model('BookingCreate', {
    'speaker_id': fields.Integer(required=True, description='Speaker ID'),
    'date': fields.String(required=True, description='Booking date (YYYY-MM-DD)'),
    'hour': fields.Integer(required=True, description='Starting hour (24-hour format)')
})

booking_model = api.model('Booking', {
    'id': fields.Integer(description='Booking ID'),
    'user_id': fields.Integer(description='User ID'),
    'speaker_id': fields.Integer(description='Speaker ID'),
    'booking_date': fields.Date(description='Booking date'),
    'start_time': fields.Integer(description='Start time'),
    'end_time': fields.Integer(description='End time'),
    'status': fields.String(description='Booking status')
})

booking_update_model = api.model('BookingUpdate', {
    'status': fields.String(required=True, description='Booking status (confirmed, cancelled, completed)')
})

# Auth routes documentation
@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(registration_model)
    @auth_ns.doc(responses={201: 'User registered successfully',
                            400: 'Invalid input',
                            409: 'Email already exists'})
    def post(self):
        """Register a new user or speaker"""
        pass

@auth_ns.route('/verify-otp')
class VerifyOTP(Resource):
    @auth_ns.expect(otp_verification_model)
    @auth_ns.doc(responses={200: 'OTP verified successfully',
                            400: 'Invalid OTP or expired',
                            404: 'User not found'})
    def post(self):
        """Verify OTP for account activation"""
        pass

@auth_ns.route('/resend-otp')
class ResendOTP(Resource):
    @auth_ns.expect(resend_otp_model)
    @auth_ns.doc(responses={200: 'OTP sent successfully',
                            400: 'User already verified',
                            404: 'User not found'})
    def post(self):
        """Resend OTP for verification"""
        pass

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.doc(responses={200: 'Login successful',
                            401: 'Invalid credentials',
                            403: 'Account not verified'})
    def post(self):
        """Login and get JWT tokens"""
        pass

@auth_ns.route('/refresh')
class RefreshToken(Resource):
    @auth_ns.doc(security='Bearer Auth', responses={200: 'Token refreshed',
                                                   401: 'Invalid refresh token'})
    def post(self):
        """Refresh access token"""
        pass

# User routes documentation
@users_ns.route('/me')
class UserProfile(Resource):
    @users_ns.doc(security='Bearer Auth', responses={200: 'User profile retrieved',
                                                    401: 'Unauthorized',
                                                    404: 'User not found'})
    def get(self):
        """Get current user profile"""
        pass
    
    @users_ns.expect(user_update_model)
    @users_ns.doc(security='Bearer Auth', responses={200: 'User profile updated',
                                                   401: 'Unauthorized',
                                                   404: 'User not found'})
    def put(self):
        """Update current user profile"""
        pass

# Speaker routes documentation
@speakers_ns.route('')
class SpeakerList(Resource):
    @speakers_ns.doc(security='Bearer Auth', responses={200: 'Speaker list retrieved',
                                                       401: 'Unauthorized'})
    def get(self):
        """Get list of all speakers"""
        pass

@speakers_ns.route('/profile')
class SpeakerProfile(Resource):
    @speakers_ns.expect(speaker_profile_model)
    @speakers_ns.doc(security='Bearer Auth', responses={200: 'Speaker profile created/updated',
                                                      401: 'Unauthorized',
                                                      403: 'Not a speaker account'})
    def post(self):
        """Create speaker profile"""
        pass
    
    @speakers_ns.expect(speaker_profile_model)
    @speakers_ns.doc(security='Bearer Auth', responses={200: 'Speaker profile updated',
                                                      401: 'Unauthorized',
                                                      403: 'Not a speaker account'})
    def put(self):
        """Update speaker profile"""
        pass

@speakers_ns.route('/<int:speaker_id>')
class SpeakerDetail(Resource):
    @speakers_ns.doc(security='Bearer Auth', responses={200: 'Speaker profile retrieved',
                                                      401: 'Unauthorized',
                                                      404: 'Speaker not found'})
    def get(self, speaker_id):
        """Get speaker profile by ID"""
        pass

@speakers_ns.route('/time-slots')
class TimeSlotList(Resource):
    @speakers_ns.doc(security='Bearer Auth', responses={200: 'Time slots retrieved',
                                                      401: 'Unauthorized',
                                                      403: 'Not a speaker account'})
    def get(self):
        """Get time slots for current speaker"""
        pass
    
    @speakers_ns.expect(time_slot_create_model)
    @speakers_ns.doc(security='Bearer Auth', responses={201: 'Time slots created',
                                                      401: 'Unauthorized',
                                                      403: 'Not a speaker account'})
    def post(self):
        """Create time slots for current speaker"""
        pass

@speakers_ns.route('/time-slots/<int:slot_id>')
class TimeSlotDetail(Resource):
    @speakers_ns.expect(time_slot_update_model)
    @speakers_ns.doc(security='Bearer Auth', responses={200: 'Time slot updated',
                                                      401: 'Unauthorized',
                                                      403: 'Not a speaker account or not owner',
                                                      404: 'Time slot not found'})
    def put(self, slot_id):
        """Update time slot availability"""
        pass

# Booking routes documentation
@bookings_ns.route('')
class BookingList(Resource):
    @bookings_ns.expect(booking_create_model)
    @bookings_ns.doc(security='Bearer Auth', responses={201: 'Booking created',
                                                       400: 'Invalid input or slot not available',
                                                       401: 'Unauthorized',
                                                       403: 'Not a user account'})
    def post(self):
        """Create a new booking"""
        pass

@bookings_ns.route('/user')
class UserBookings(Resource):
    @bookings_ns.doc(security='Bearer Auth', responses={200: 'Bookings retrieved',
                                                       401: 'Unauthorized'})
    def get(self):
        """Get bookings for current user (as user or speaker)"""
        pass

@bookings_ns.route('/<int:booking_id>')
class BookingDetail(Resource):
    @bookings_ns.doc(security='Bearer Auth', responses={200: 'Booking retrieved',
                                                       401: 'Unauthorized',
                                                       403: 'Not authorized to view this booking',
                                                       404: 'Booking not found'})
    def get(self, booking_id):
        """Get booking by ID"""
        pass
    
    @bookings_ns.expect(booking_update_model)
    @bookings_ns.doc(security='Bearer Auth', responses={200: 'Booking status updated',
                                                       401: 'Unauthorized',
                                                       403: 'Not authorized to update this booking',
                                                       404: 'Booking not found'})
    def put(self, booking_id):
        """Update booking status"""
        pass
