from django.urls import path
from . import views

urlpatterns = [
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/slot/create/', views.create_slot, name='create_slot'),
    path('doctor/slot/<int:slot_id>/delete/', views.delete_slot, name='delete_slot'),
    path('patient/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/book/<int:slot_id>/', views.book_slot, name='book_slot'),
]       