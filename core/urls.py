from django.urls import path

from core.views.admin.club.views import club
from core.views.admin.index.views import IndexAdminView
from core.views.admin.reserva.views import *
from core.views.user.index.views import IndexView
from parameters.views import ParametersClubFormView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('admin/', IndexAdminView.as_view(), name='index_admin'),

    # URLs del club (administración)
    path('admin/club/', lambda request: redirect('admin-club-detalles', permanent=True), name='club'),
    path('admin/club/detalles/', club, name='admin-club-detalles'),
    path('admin/club/parametros/', ParametersClubFormView.as_view(), name='admin-club-parametros'),

    # URLs de las reservas (administración)
    path('admin/reservas/', lambda request: redirect('admin-reservas-listado', permanent=True), name='admin-reservas'),
    path('admin/reservas/listado', ReservaAdminListView.as_view(), name='admin-reservas-listado'),
    path('admin/reservas/crear', ReservaAdminCreateView.as_view(), name='admin-reservas-crear'),
    path('admin/reservas/<int:pk>/', ReservaAdminDetailView.as_view(), name='admin-reservas-detalle'),
    path('admin/reservas/<int:pk>/editar', ReservaAdminUpdateView.as_view(), name='admin-reservas-editar'),
    path('admin/reservas/<int:pk>/baja', ReservaAdminDeleteView.as_view(), name='admin-reservas-baja'),
    path('admin/reservas/ajax/', reserva_admin_ajax, name='admin-reservas-ajax'),
]
