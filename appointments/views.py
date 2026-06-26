from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
import datetime

from .models import AvailabilitySlot, Booking
from .forms import AvailabilitySlotForm
from .email_service import send_booking_confirmation
from .google_calendar import create_booking_events


def doctor_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_doctor():
            messages.error(request, "Access denied. Doctors only.")
            return redirect('patient_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def patient_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_patient():
            messages.error(request, "Access denied. Patients only.")
            return redirect('doctor_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@doctor_required
def doctor_dashboard(request):
    today = datetime.date.today()
    slots = AvailabilitySlot.objects.filter(
        doctor=request.user,
        date__gte=today,
    ).order_by('date', 'start_time')
    return render(request, 'appointments/doctor_dashboard.html', {'slots': slots})


@doctor_required
def create_slot(request):
    if request.method == 'POST':
        form = AvailabilitySlotForm(request.POST)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.doctor = request.user
            slot.save()
            messages.success(request, f"Slot added: {slot.date} {slot.start_time}–{slot.end_time}")
            return redirect('doctor_dashboard')
    else:
        form = AvailabilitySlotForm()
    return render(request, 'appointments/create_slot.html', {'form': form})


@doctor_required
def delete_slot(request, slot_id):
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, doctor=request.user)
    if slot.status == AvailabilitySlot.STATUS_BOOKED:
        messages.error(request, "Cannot delete a booked slot.")
    else:
        slot.delete()
        messages.success(request, "Slot deleted.")
    return redirect('doctor_dashboard')


@patient_required
def patient_dashboard(request):
    today = datetime.date.today()
    available_slots = AvailabilitySlot.objects.filter(
        status=AvailabilitySlot.STATUS_AVAILABLE,
        date__gte=today,
    ).select_related('doctor').order_by('date', 'start_time')

    my_bookings = Booking.objects.filter(
        patient=request.user,
        status=Booking.STATUS_CONFIRMED,
    ).select_related('slot', 'slot__doctor').order_by('slot__date')

    return render(request, 'appointments/patient_dashboard.html', {
        'available_slots': available_slots,
        'my_bookings': my_bookings,
    })


@patient_required
def book_slot(request, slot_id):
    with transaction.atomic():
        slot = get_object_or_404(
            AvailabilitySlot.objects.select_for_update(),
            id=slot_id,
        )

        if not slot.is_available():
            messages.error(request, "Sorry, this slot was just booked by someone else.")
            return redirect('patient_dashboard')

        already_booked = Booking.objects.filter(
            patient=request.user,
            slot__doctor=slot.doctor,
            slot__date=slot.date,
            status=Booking.STATUS_CONFIRMED,
        ).exists()
        if already_booked:
            messages.error(request, "You already have a booking with this doctor on this date.")
            return redirect('patient_dashboard')

        booking = Booking.objects.create(slot=slot, patient=request.user)
        slot.status = AvailabilitySlot.STATUS_BOOKED
        slot.save(update_fields=['status'])

    try:
        create_booking_events(booking)
    except Exception as e:
        print(f"[Calendar] {e}")

    try:
        send_booking_confirmation(booking)
    except Exception as e:
        print(f"[Email] {e}")

    messages.success(request, f"Booked! Appointment with Dr. {slot.doctor.get_full_name()} on {slot.date} at {slot.start_time}.")
    return redirect('patient_dashboard')