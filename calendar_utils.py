from __future__ import print_function
import datetime
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# OAuth 2.0 scope for full calendar access
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Path to your token and credentials
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

# Doctor's calendar ID
CALENDAR_ID = 'primary'

def get_calendar_service():
    """Returns an authenticated Google Calendar service using OAuth 2.0."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def get_slot_datetime(date_str, time_str, duration_minutes=20):
    """
    Returns start and end datetime strings in ISO 8601 format for the given slot.
    Example: get_slot_datetime("2025-04-25", "10:20")
    """
    start_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
    return start_dt.isoformat(), end_dt.isoformat()

def create_event(start_time, end_time, summary, patient_email):
    """
    Creates a calendar event and invites the doctor and patient via email.
    Returns the event link.
    """
    service = get_calendar_service()

    event = {
        'summary': summary,
        'description': 'Doctor Appointment via AI Agent',
        'start': {
            'dateTime': start_time,
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'Asia/Kolkata',
        },
        'attendees': [
            {'email': patient_email},
            {'email': 'vatsalmahajan0007@gmail.com'},
        ],
    }

    event_result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    return event_result.get('htmlLink')
