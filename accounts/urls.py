from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('google/connect/', views.google_connect_view, name='google_connect'),
    path('google/callback/', views.google_callback_view, name='google_callback'),
]