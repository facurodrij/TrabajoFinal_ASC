from django.urls import path
from django.contrib.auth import views

from .views import *
from .decorators import *

urlpatterns = [
    path('register/', no_login_required(RegisterView.as_view()), name='register'),
    path('perfil/', profile, name='profile'),
    path('login/', no_login_required(CustomLoginView.as_view()), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Password urls
    path('password_change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password_reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
