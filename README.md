# Mini Hospital Management System (HMS)

A Django-based hospital management system with doctor availability, patient appointment booking, Google Calendar integration, and a serverless email notification service.

---

## Setup and Run

### Prerequisites
- Python 3.10+
- PostgreSQL installed and running locally
- Node.js 18+

### 1. Clone the repository
```bash
git clone https://github.com/Aisha-30/hms-project.git
cd hms-project
```

### 2. Create virtual environment and install dependencies
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set up PostgreSQL
Open psql and run:
```sql
CREATE DATABASE hms_db;
```

### 4. Create .env file in root folder

DJANGO_SECRET_KEY=your-secret-key-here

DB_NAME=hms_db

DB_USER=postgres

DB_PASSWORD=yourpassword

DB_HOST=localhost

DB_PORT=5432

EMAIL_SERVICE_URL=http://localhost:3000/dev/send-email

GOOGLE_CLIENT_ID=your-google-client-id

GOOGLE_CLIENT_SECRET=your-google-client-secret

GOOGLE_REDIRECT_URI=http://localhost:8000/accounts/google/callback/

### 5. Run migrations
```bash
python manage.py makemigrations accounts
python manage.py makemigrations appointments
python manage.py migrate
```

### 6. Start Django server
```bash
python manage.py runserver
```
App runs at http://localhost:8000

### 7. Start Serverless email service (separate terminal)
```bash
cd email-service
npm install
npx serverless offline
```
Email service runs at http://localhost:3000

### 8. Google Calendar (optional)
1. Go to Google Cloud Console
2. Enable Google Calendar API
3. Create OAuth2 credentials (Web Application)
4. Add redirect URI: http://localhost:8000/accounts/google/callback/
5. Copy Client ID and Secret to .env file
6. After login click "Connect Google Calendar" in navbar

---

## System Architecture

Browser (Doctor / Patient)

↓ HTTP

Django App (localhost:8000)

├── accounts/     → Signup, login, Google OAuth2 flow

├── appointments/ → Slots, bookings, race condition handling

↓ ORM           ↓ HTTP POST          ↓ Google API

PostgreSQL      Email Service         Google Calendar

(localhost:3000)          (OAuth2)

### Data Models

**User** (custom, extends AbstractUser)
- role: doctor or patient
- google_access_token, google_refresh_token, google_token_expiry

**AvailabilitySlot**
- doctor (FK to User)
- date, start_time, end_time
- status: available or booked
- unique_together: (doctor, date, start_time) — no duplicate slots

**Booking**
- slot (OneToOneField) — one slot = maximum one booking ever
- patient (FK to User)
- patient_calendar_event_id, doctor_calendar_event_id

### Role-Based Access
- @doctor_required decorator blocks patients from doctor pages
- @patient_required decorator blocks doctors from patient pages
- Doctors only see their own slots via filter(doctor=request.user)

### Google Calendar Integration
1. User clicks Connect Google Calendar
2. Redirected to Google consent screen
3. Google sends authorization code back to our callback URL
4. We exchange code for access + refresh tokens
5. Tokens stored on User model
6. On booking confirmation — events created on both calendars

### Serverless Email Service
- Separate Python script in email-service/handler.py
- Defined as AWS Lambda function in serverless.yml
- Run locally via npx serverless offline on port 3000
- Django calls it via HTTP POST request
- Supports SIGNUP_WELCOME and BOOKING_CONFIRMATION triggers

---

## The Design Decision

### Race Condition in Slot Booking

**The Problem:**
Two patients open the same slot simultaneously. Both see status=available. Both click Book. Without protection both create a booking — double booking disaster.

**Option A: Application-level locking**
Create a lock table or use Redis. Insert a lock row when booking starts. Delete when done.

Problems:
- Extra table and extra queries
- Orphaned locks if process crashes mid-booking
- Still does not prevent two simultaneous reads both seeing available

**Option B: Database-level locking with select_for_update() — chosen**
Inside transaction.atomic(), use select_for_update() to lock the PostgreSQL row. When Patient A locks the row, Patient B waits. After Patient A commits and sets status=booked, Patient B resumes, reads status=booked, and gets rejected.

**Why Option B is better:**
The check and update happen inside one atomic transaction — impossible to race between them. PostgreSQL handles the locking natively. No extra dependencies needed. This is exactly what database transactions are designed for. Application-level locks don't give you atomicity between the read and write operations.

---

## Limitations

1. **Google token storage** — OAuth2 tokens stored as plain text in database. Production needs encrypted storage.

2. **Email reliability** — If serverless function is down, emails are silently dropped. Production needs a queue like SQS or Celery for retries.

3. **No booking cancellation** — Patients and doctors cannot cancel confirmed bookings. Needs a cancellation flow with calendar event deletion.

4. **No pagination** — All available slots loaded in one query. With thousands of slots this would be slow. Needs pagination.

5. **Session storage** — Django database sessions do not scale horizontally. Production needs Redis for session storage.
