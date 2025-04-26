from __future__ import print_function
import datetime
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timedelta

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
    
def is_slot_available(date, time):
    # Assuming datetime format: YYYY-MM-DD, HH:MM
    start = f"{date}T{time}:00"
    end_dt = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M") + datetime.timedelta(minutes=20)
    end = end_dt.isoformat()

    service = get_calendar_service()
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    return len(events) == 0  # True if no conflicts


def is_valid_appointment(date_str, time_str):
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        weekday = dt.weekday()  # Monday = 0, Sunday = 6
        hour = dt.hour

        if weekday == 6:
            return False, "Sunday"
        elif 14 <= hour < 16:
            return False, "Lunch Break"
        elif 10 <= hour < 14 or 15 <= hour < 19:
            return True, None
        else:
            return False, "Outside Hours"
    except Exception:
        return False, "Invalid Format"

def find_and_cancel_appointment(email):
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    service = build("calendar", "v3", credentials=creds)

    events_result = service.events().list(
        calendarId="primary",
        q=email,
        maxResults=10,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])

    for event in events:
        if email in event.get("description", ""):
            service.events().delete(calendarId="primary", eventId=event["id"]).execute()
            return True
    return False



SERVICE_ACCOUNT_FILE = 'credentials.json'  # Your credentials file

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=credentials)

def find_upcoming_appointment_by_email(email):
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime',
        q=email
    ).execute()
    events = events_result.get('items', [])
    if events:
        return events[0]  # Assume the first match is the one to cancel
    return None

def cancel_event(event_id):
    try:
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return True
    except Exception as e:
        print("Error canceling event:", e)
        return False
