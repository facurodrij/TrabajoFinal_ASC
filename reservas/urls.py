from django.shortcuts import redirect
from django.urls import path

from reservas.views.admin.reserva.views import ReservaAdminListView, ReservaAdminCreateView, ReservaAdminDetailView, \
    ReservaAdminUpdateView, ReservaAdminDeleteView, reserva_admin_ajax
from reservas.views.user.reserva.views import ReservaUserListView, ReservaUserCreateView, ReservaUserDetailView, \
    ReservaUserDeleteView, ReservaUserPaymentView, ReservaCheckoutView, ReservaUserReceiptView, \
    reserva_liberada_activate

urlpatterns = [

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
    path('reservas/<uuid:pk>/baja/', ReservaUserDeleteView.as_view(), name='reservas-baja'),
    path('reservas/<uuid:pk>/pago/', ReservaUserPaymentView.as_view(), name='reservas-pago'),
    path('reservas/checkout/', ReservaCheckoutView.as_view(), name='reservas-checkout'),
    path('reservas/<uuid:pk>/comprobante/', ReservaUserReceiptView.as_view(), name='reservas-comprobante'),

    # URLs para el proceso automatizado de reserva de cancha liberada.
    path('reservas/<uidb64>/<token>/', reserva_liberada_activate, name='reserva-liberada-activate'),
]
