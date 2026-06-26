import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_email(event_type, recipient_email, recipient_name, **extra):
    payload = {
        'event_type': event_type,
        'recipient_email': recipient_email,
        'recipient_name': recipient_name,
        **extra,
    }
    try:
        response = requests.post(settings.EMAIL_SERVICE_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"[Email] {event_type} sent to {recipient_email}")
        return True
    except requests.exceptions.ConnectionError:
        logger.warning(f"[Email] Service not running. Skipped {event_type} for {recipient_email}")
        return False
    except Exception as e:
        logger.error(f"[Email] Error: {e}")
        return False


def send_signup_welcome(user):
    return send_email('SIGNUP_WELCOME', user.email, user.get_full_name(), role=user.role)


def send_booking_confirmation(booking):
    slot = booking.slot
    send_email(
        'BOOKING_CONFIRMATION',
        booking.patient.email,
        booking.patient.get_full_name(),
        other_party_name=f"Dr. {slot.doctor.get_full_name()}",
        date=str(slot.date),
        start_time=str(slot.start_time),
        end_time=str(slot.end_time),
        role='patient',
    )
    send_email(
        'BOOKING_CONFIRMATION',
        slot.doctor.email,
        f"Dr. {slot.doctor.get_full_name()}",
        other_party_name=booking.patient.get_full_name(),
        date=str(slot.date),
        start_time=str(slot.start_time),
        end_time=str(slot.end_time),
        role='doctor',
    )