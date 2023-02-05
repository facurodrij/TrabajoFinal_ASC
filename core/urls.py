from django.shortcuts import redirect
from django.urls import path

from core.views.admin.club.views import ClubFormView
from core.views.admin.estadistica.views import EstadisticaAdminView
from core.views.admin.index.views import IndexAdminView
from core.views.user.index.views import IndexView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('admin/', IndexAdminView.as_view(), name='index_admin'),

    # URLs del club (administración)
    path('admin/club/', lambda request: redirect('admin-club-form', permanent=True), name='club'),
    path('admin/club/detalles/', ClubFormView.as_view(), name='admin-club-form'),

    path('admin/estadisticas/', EstadisticaAdminView.as_view(), name='admin-estadisticas'),
]
