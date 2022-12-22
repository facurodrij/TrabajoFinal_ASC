from django.contrib.auth import views
from django.urls import path

from .views import *

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('activate/<uidb64>/<token>/', activate_account, name='activate'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('persona/', persona_view, name='persona'),

    # Password urls
    path('password_change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password_reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # URLs de persona (administración)
    path('admin/personas/', lambda request: redirect('admin-persona-listado', permanent=True), name='admin-persona'),
    path('admin/personas/listado/', PersonaAdminListView.as_view(), name='admin-persona-listado'),
    path('admin/personas/crear/', PersonaAdminCreateView.as_view(), name='admin-persona-crear'),
    # path('admin/club/personas/<int:pk>/', PersonaAdminDetailView.as_view(), name='admin-club-persona-detalle'),
    path('admin/personas/<int:pk>/editar/', PersonaAdminUpdateView.as_view(), name='admin-persona-editar'),
]
