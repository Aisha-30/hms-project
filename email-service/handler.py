import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(event, context):
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
    except Exception:
        return _resp(400, {'error': 'Invalid JSON'})

    event_type = body.get('event_type')
    recipient_email = body.get('recipient_email')
    recipient_name = body.get('recipient_name', 'User')

    if not event_type or not recipient_email:
        return _resp(400, {'error': 'event_type and recipient_email required'})

    if event_type == 'SIGNUP_WELCOME':
        subject, html = _welcome(recipient_name, body.get('role', 'user'))
    elif event_type == 'BOOKING_CONFIRMATION':
        subject, html = _booking(
            recipient_name,
            body.get('other_party_name', ''),
            body.get('date', ''),
            body.get('start_time', ''),
            body.get('end_time', ''),
            body.get('role', 'patient'),
        )
    else:
        return _resp(400, {'error': f'Unknown event_type: {event_type}'})

    ok = _smtp(recipient_email, subject, html)
    if ok:
        return _resp(200, {'message': f'Sent {event_type} to {recipient_email}'})
    return _resp(500, {'error': 'SMTP failed'})


def _welcome(name, role):
    subject = "Welcome to HMS!"
    html = f"""<html><body style="font-family:sans-serif">
    <h2>Welcome, {name}! 🏥</h2>
    <p>Your account is ready as a <strong>{role}</strong>.</p>
    {"<p>You can now add your availability slots.</p>" if role == "doctor" else "<p>You can now browse and book appointments.</p>"}
    </body></html>"""
    return subject, html


def _booking(name, other, date, start, end, role):
    if role == 'patient':
        subject = f"Appointment Confirmed with {other}"
        intro = f"Your appointment with <strong>{other}</strong> is confirmed."
    else:
        subject = f"New Appointment with {other}"
        intro = f"You have a new appointment with <strong>{other}</strong>."
    html = f"""<html><body style="font-family:sans-serif">
    <h2>Appointment Confirmed ✅</h2>
    <p>Dear {name},</p><p>{intro}</p>
    <div style="background:#f0f3ff;padding:1rem;border-radius:8px;margin:1rem 0">
        <p><strong>Date:</strong> {date}</p>
        <p><strong>Time:</strong> {start} – {end}</p>
    </div>
    <p style="color:#888">— HMS</p></body></html>"""
    return subject, html


def _smtp(to, subject, html):
    host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    port = int(os.environ.get('SMTP_PORT', 587))
    user = os.environ.get('SMTP_USER', '')
    pwd = os.environ.get('SMTP_PASSWORD', '')
    frm = os.environ.get('FROM_EMAIL', user)

    if not user or not pwd:
        print(f"\n{'='*50}")
        print(f"[EMAIL SIMULATION - No SMTP configured]")
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print(f"{'='*50}\n")
        return True

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = frm
        msg['To'] = to
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, pwd)
            server.sendmail(frm, to, msg.as_string())
        print(f"[EMAIL SENT] {subject} → {to}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def _resp(code, body):
    return {
        'statusCode': code,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body),
    }