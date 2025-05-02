import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app import app

# Scopes required for Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_google_auth_url():
    """Generate the authorization URL for Google OAuth."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": app.config.get('GOOGLE_CLIENT_ID'),
                "client_secret": app.config.get('GOOGLE_CLIENT_SECRET'),
                "redirect_uris": [app.config.get('GOOGLE_REDIRECT_URI')],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES
    )
    
    flow.redirect_uri = app.config.get('GOOGLE_REDIRECT_URI')
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    return authorization_url, state

def get_credentials_from_code(code):
    """Exchange authorization code for credentials."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": app.config.get('GOOGLE_CLIENT_ID'),
                "client_secret": app.config.get('GOOGLE_CLIENT_SECRET'),
                "redirect_uris": [app.config.get('GOOGLE_REDIRECT_URI')],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES
    )
    
    flow.redirect_uri = app.config.get('GOOGLE_REDIRECT_URI')
    
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return credentials
    except Exception as e:
        app.logger.error(f"Error getting credentials from code: {str(e)}")
        return None

def create_calendar_event(credentials_dict, booking):
    """
    Create a Google Calendar event for a booking.
    
    Args:
        credentials_dict: Dictionary containing OAuth2 credentials
        booking: Booking model instance
    
    Returns:
        event_id: ID of the created calendar event
    """
    try:
        # Create credentials from dict
        credentials = Credentials(
            token=credentials_dict.get('token'),
            refresh_token=credentials_dict.get('refresh_token'),
            token_uri=credentials_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=app.config.get('GOOGLE_CLIENT_ID'),
            client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
            scopes=SCOPES
        )
        
        # Build the service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Get user and speaker information
        user = booking.user
        speaker = booking.speaker
        
        # Format date and time for the event
        booking_date = booking.booking_date
        start_time = datetime.datetime.combine(
            booking_date, 
            datetime.time(hour=booking.start_time)
        ).isoformat()
        end_time = datetime.datetime.combine(
            booking_date, 
            datetime.time(hour=booking.end_time)
        ).isoformat()
        
        # Create event details
        event = {
            'summary': f'Speaker Session: {speaker.first_name} {speaker.last_name}',
            'location': 'Virtual',
            'description': f'Speaker session with {speaker.first_name} {speaker.last_name}',
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': user.email},
                {'email': speaker.email},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }
        
        # Create the event
        event = service.events().insert(calendarId='primary', body=event, sendNotifications=True).execute()
        
        return event.get('id')
    
    except HttpError as error:
        app.logger.error(f'An error occurred while creating calendar event: {error}')
        return None
    
    except Exception as e:
        app.logger.error(f'Unexpected error creating calendar event: {str(e)}')
        return None

def create_mock_calendar_event(booking):
    """
    Create a mock calendar event when Google Calendar integration is not available.
    This is used in development or when Google Calendar credentials are not set up.
    
    Args:
        booking: Booking model instance
    
    Returns:
        event_id: A mock event ID
    """
    import uuid
    # Generate a mock event ID
    mock_event_id = f"mock-event-{uuid.uuid4()}"
    
    # Log the mock event creation
    app.logger.info(f"Created mock calendar event with ID: {mock_event_id} for booking ID: {booking.id}")
    
    return mock_event_id
