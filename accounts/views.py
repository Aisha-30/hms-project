from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.conf import settings

from .forms import SignUpForm
from appointments.email_service import send_signup_welcome
from appointments.google_calendar import get_authorization_url, exchange_code_for_tokens


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            send_signup_welcome(user)
            messages.success(request, f"Welcome, {user.get_full_name()}!")
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_doctor():
        return redirect('doctor_dashboard')
    return redirect('patient_dashboard')


def google_connect_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not settings.GOOGLE_CLIENT_ID:
        messages.warning(request, "Google Calendar not configured in .env")
        return redirect('dashboard')
    auth_url, state = get_authorization_url()
    request.session['google_oauth_state'] = state
    return redirect(auth_url)


def google_callback_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    code = request.GET.get('code')
    error = request.GET.get('error')
    if error:
        messages.error(request, f"Google auth failed: {error}")
        return redirect('dashboard')
    if not code:
        messages.error(request, "No code from Google.")
        return redirect('dashboard')
    try:
        token_data = exchange_code_for_tokens(code)
        u = request.user
        u.google_access_token = token_data['access_token']
        u.google_refresh_token = token_data['refresh_token']
        u.google_token_expiry = token_data['expiry']
        u.save(update_fields=['google_access_token', 'google_refresh_token', 'google_token_expiry'])
        messages.success(request, "Google Calendar connected!")
    except Exception as e:
        messages.error(request, f"Failed: {e}")
    return redirect('dashboard')