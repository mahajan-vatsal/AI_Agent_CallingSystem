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

def get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credentials)


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
        'location': 'Clinic Address Here',
        'description': 'Doctor Appointment Booking via AI Agent.',
        'start': {
            'dateTime': start_time,
            'timeZone': TIMEZONE,
        },
        'end': {
            'dateTime': end_time,
            'timeZone': TIMEZONE,
        },
        'attendees': [
            {'email': patient_email},
            {'email': 'vatsalmahajan0007@gmail.com'},
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    try:
        event = service_oauth.events().insert(
            calendarId=CALENDAR_ID, body=event, sendUpdates='all'
        ).execute()
        print('✅ Event created:', event.get('htmlLink'))
        return event
    except Exception as e:
        print(f"❌ Failed to create event: {e}")
        return None

def cancel_event(event_id):
    """
    Cancels an existing event using the same OAuth service that created it.
    """
    try:
        service_oauth.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        print(f"✅ Event {event_id} canceled successfully.")
        return True
    except Exception as e:
        print(f"❌ Error canceling event {event_id}: {type(e).__name__} - {e}")
        return False





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
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    events_result = service_oauth.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        maxResults=20,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    for event in events:
        attendees = event.get('attendees', [])
        attendee_emails = [a.get('email', '').lower() for a in attendees]

        if email.lower() in attendee_emails:
            print(f"✅ Found appointment for {email}")
            return event

    print(f"❌ No appointment found for {email}")
    return None


def is_email_already_booked(service, calendar_id, email):
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now,
        maxResults=100,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    for event in events:
        if 'attendees' in event:
            for attendee in event['attendees']:
                if attendee.get('email') == email:
                    return True
    return False




#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# For testing purposes


def list_all_upcoming_appointments():
    from datetime import datetime
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service_oauth.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        maxResults=50,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    if not events:
        print("No upcoming events found.")
        return

    for event in events:
        print("\n📅 Event:", event.get('summary'))
        print("🕒 Start:", event['start'].get('dateTime'))
        attendees = event.get('attendees', [])
        print("👥 Attendees:", [a.get('email') for a in attendees])
