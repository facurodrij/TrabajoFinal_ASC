from django.urls import path
from django.contrib.auth import views

from .views import *

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('activate/<uidb64>/<token>', activate, name='activate'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('persona/', persona, name='persona'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Password urls
    path('password_change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password_reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
