from django.urls import path

from core.views.admin.club.views import club
from core.views.admin.evento.views import *
from core.views.admin.index.views import IndexAdminView
from core.views.admin.reserva.views import *
from core.views.user.index.views import IndexView
from core.views.user.reserva.views import *
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
    path('admin/reservas/listado/', ReservaAdminListView.as_view(), name='admin-reservas-listado'),
    path('admin/reservas/crear/', ReservaAdminCreateView.as_view(), name='admin-reservas-crear'),
    path('admin/reservas/<uuid:pk>/', ReservaAdminDetailView.as_view(), name='admin-reservas-detalle'),
    path('admin/reservas/<uuid:pk>/editar/', ReservaAdminUpdateView.as_view(), name='admin-reservas-editar'),
    path('admin/reservas/<uuid:pk>/baja/', ReservaAdminDeleteView.as_view(), name='admin-reservas-baja'),
    path('admin/reservas/ajax/', reserva_admin_ajax, name='admin-reservas-ajax'),

    # URLs de las reservas (usuarios)
    path('reservas/', lambda request: redirect('reservas-listado', permanent=True), name='reservas'),
    path('reservas/listado/', ReservaUserListView.as_view(), name='reservas-listado'),
    path('reservas/crear/', ReservaUserCreateView.as_view(), name='reservas-crear'),
    path('reservas/<uuid:pk>/', ReservaUserDetailView.as_view(), name='reservas-detalle'),
    # path('reservas/<int:pk>/editar', ReservaUpdateView.as_view(), name='reservas-editar'),
    path('reservas/<uuid:pk>/baja/', ReservaUserDeleteView.as_view(), name='reservas-baja'),
    # path('reservas/ajax/', reserva_ajax, name='reservas-ajax'),
    path('reservas/<uuid:pk>/pago/', ReservaUserPaymentView.as_view(), name='reservas-pago'),
    path('reservas/checkout/', ReservaCheckoutView.as_view(), name='reservas-checkout'),

    # URLs para el proceso automatizado de reserva de cancha liberada.
    path('reservas/<uidb64>/<token>/', reserva_liberada_activate, name='reserva-liberada-activate'),

    # URLs de los evetos (administración)
    path('admin/eventos/', lambda request: redirect('admin-eventos-listado', permanent=True), name='admin-eventos'),
    path('admin/eventos/listado/', EventoAdminListView.as_view(), name='admin-eventos-listado'),
    path('admin/eventos/crear/', EventoAdminCreateView.as_view(), name='admin-eventos-crear'),
    path('admin/eventos/<int:pk>/editar/', EventoAdminUpdateView.as_view(), name='admin-eventos-editar'),
]
