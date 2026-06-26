# AI Tool Usage Log — Claude

Tool used: Claude (claude.ai)

## What I used Claude for:

1. Architecture planning — how to structure Django apps, models, URLs
2. Custom User model — why extend AbstractUser, what AUTH_USER_MODEL does
3. Race condition fix — select_for_update() explanation and implementation
4. Google Calendar OAuth2 — full flow from authorization to token storage
5. Serverless email — how handler.py works as a Lambda function
6. Git setup — how to push code to GitHub

## Key things I understood and can explain:

### Race Condition (select_for_update)
Two patients try to book the same slot simultaneously.
select_for_update() locks the database row inside transaction.atomic().
First patient locks the row, second patient waits.
First patient sets status=booked and commits.
Second patient reads status=booked and gets rejected.
The check and update are atomic — impossible to race.

### Custom User Model
We extend AbstractUser to add a role field (doctor/patient).
AUTH_USER_MODEL must be set before the first migration.
Changing it after breaks all existing migrations.

### Serverless Email
handler.py is a completely separate Python function.
Django calls it via HTTP POST to localhost:3000/dev/send-email.
If email service is down, booking still succeeds (we catch ConnectionError).
Supports SIGNUP_WELCOME and BOOKING_CONFIRMATION event types.

### Google Calendar OAuth2
User clicks Connect → Google consent screen.
Google sends authorization code to our callback URL.
We exchange code for access + refresh tokens.
Tokens stored on User model.
On booking — events created on both doctor and patient calendars.
