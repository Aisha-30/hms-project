from django.contrib import admin
from django.urls import path, include
from accounts.views import dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('appointments/', include('appointments.urls')),
    path('', dashboard_view, name='dashboard'),
]