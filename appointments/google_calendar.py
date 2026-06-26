import datetime
from django.conf import settings

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/calendar.events']


def get_google_auth_flow():
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    return flow


def get_authorization_url():
    if not GOOGLE_AVAILABLE or not settings.GOOGLE_CLIENT_ID:
        return '#', 'no-state'
    flow = get_google_auth_flow()
    auth_url, state = flow.authorization_url(access_type='offline', prompt='consent')
    return auth_url, state


def exchange_code_for_tokens(code):
    flow = get_google_auth_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        'access_token': creds.token,
        'refresh_token': creds.refresh_token,
        'expiry': creds.expiry,
    }


def get_credentials_for_user(user):
    if not GOOGLE_AVAILABLE or not user.google_access_token:
        return None
    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        user.google_access_token = creds.token
        user.google_token_expiry = creds.expiry
        user.save(update_fields=['google_access_token', 'google_token_expiry'])
    return creds


def create_calendar_event(user, title, start_dt, end_dt, description=''):
    creds = get_credentials_for_user(user)
    if not creds:
        return None
    try:
        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': title,
            'description': description,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
        }
        result = service.events().insert(calendarId='primary', body=event).execute()
        return result.get('id')
    except Exception as e:
        print(f"[Calendar Error] {e}")
        return None


def create_booking_events(booking):
    slot = booking.slot
    tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    start_dt = datetime.datetime.combine(slot.date, slot.start_time).replace(tzinfo=tz)
    end_dt = datetime.datetime.combine(slot.date, slot.end_time).replace(tzinfo=tz)

    patient_event_id = create_calendar_event(
        booking.patient,
        f"Appointment with Dr. {slot.doctor.get_full_name()}",
        start_dt, end_dt,
    )
    doctor_event_id = create_calendar_event(
        slot.doctor,
        f"Appointment with {booking.patient.get_full_name()}",
        start_dt, end_dt,
    )
    if patient_event_id or doctor_event_id:
        booking.patient_calendar_event_id = patient_event_id
        booking.doctor_calendar_event_id = doctor_event_id
        booking.save(update_fields=['patient_calendar_event_id', 'doctor_calendar_event_id'])
    return patient_event_id, doctor_event_id