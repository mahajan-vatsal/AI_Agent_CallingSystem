from __future__ import print_function
import os
from datetime import datetime, timedelta
import pytz

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Constants
SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'agentic-ai-caller.json'
SERVICE_ACCOUNT_FILE = 'agentic-ai-caller.json'
CALENDAR_ID = 'primary'
TIMEZONE = 'Asia/Kolkata'

# Initialize Service Account
service_account_credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# Initialize OAuth 2.0 (user-based) credentials
def init_oauth_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    # If no valid creds, ask user to login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds)
    return service

# Create global services once
service_oauth = init_oauth_service()
service_account_service = build('calendar', 'v3', credentials=service_account_credentials)

def get_slot_datetime(date_str, time_str, duration_minutes=20):
    """
    Returns start and end datetime strings in ISO 8601 format with timezone.
    """
    local_tz = pytz.timezone(TIMEZONE)
    start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    start_dt = local_tz.localize(start_dt)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return start_dt.isoformat(), end_dt.isoformat()

def create_event(start_time, end_time, summary, patient_email):
    event = {
        'summary': summary,
        'location': 'Clinic Address Here',  # Optional: you can customize this
        'description': 'Doctor Appointment Booking via AI Agent.',  # You can customize
        'start': {
            'dateTime': start_time,
            'timeZone': 'Asia/Kolkata',  # Change if needed
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'Asia/Kolkata',
        },
        'attendees': [
            {'email': patient_email},
            {'email': 'vatsalmahajan0007@gmail.com'},  # Doctor's email (fixed)
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                {'method': 'popup', 'minutes': 10},       # 10 minutes before
            ],
        },
    }
    
    event = service_oauth.events().insert(calendarId='primary', body=event, sendUpdates='all').execute()
    print('✅ Event created:', event.get('htmlLink'))
    return event




def is_slot_available(date_str, time_str, duration_minutes=20):
    """
    Checks if a time slot is free.
    """
    local_tz = pytz.timezone(TIMEZONE)
    start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    start_dt = local_tz.localize(start_dt)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    events_result = service_oauth.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_dt.isoformat(),
        timeMax=end_dt.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    return len(events) == 0

def is_valid_appointment(date_str, time_str):
    """
    Validates appointment within business hours.
    """
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        weekday = dt.weekday()
        hour = dt.hour

        if weekday == 6:
            return False, "Sunday"
        elif 14 <= hour < 16:
            return False, "Lunch Break"
        elif (10 <= hour < 14) or (16 <= hour < 19):
            return True, None
        else:
            return False, "Outside Hours"
    except Exception:
        return False, "Invalid Format"

def find_upcoming_appointment_by_email(email):
    """
    Finds the next upcoming appointment by email.
    """
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service_account_service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime',
        q=email
    ).execute()
    events = events_result.get('items', [])
    return events[0] if events else None

def cancel_event(event_id):
    """
    Cancels an existing event.
    """
    try:
        service_account_service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return True
    except Exception as e:
        print(f"Error canceling event: {e}")
        return False
