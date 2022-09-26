from django.urls import path
from django.views.generic import TemplateView

from .views import *

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('clubes/', ClubListView.as_view(), name='club_list'),
    path('club/crear/', ClubCreateView.as_view(), name='club_create'),
    path('club/actualizar/<int:pk>/', ClubUpdateView.as_view(), name='club_update'),
    path('club/eliminar/<int:pk>/', club_delete, name='club_delete'),
    path('club/restore/<int:pk>/', club_restore, name='club_restore'),
]
