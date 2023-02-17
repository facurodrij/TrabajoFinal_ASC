from django.urls import path

from eventos.views.admin.evento.views import *
from eventos.views.admin.ticket.views import *
from eventos.views.user.evento.views import *

urlpatterns = [
    # URLs de los eventos (administración)
    path('admin/eventos/', lambda request: redirect('admin-eventos-listado', permanent=True), name='admin-eventos'),
    path('admin/eventos/listado/', EventoAdminListView.as_view(), name='admin-eventos-listado'),
    path('admin/eventos/crear/', EventoAdminCreateView.as_view(), name='admin-eventos-crear'),
    path('admin/eventos/<int:pk>/editar/', EventoAdminUpdateView.as_view(), name='admin-eventos-editar'),
    path('admin/eventos/<int:pk>/baja/', EventoAdminDeleteView.as_view(), name='admin-eventos-baja'),

    path('admin/tickets/', lambda request: redirect('admin-tickets-listado', permanent=True), name='admin-tickets'),
    path('admin/tickets/listado/', TicketAdminListView.as_view(), name='admin-tickets-listado'),
    path('admin/tickets/<int:pk>/', TicketAdminDetailView.as_view(), name='admin-tickets-detalle'),
    path('admin/tickets/<int:pk>/qr/', TicketAdminQRView.as_view(), name='admin-tickets-qr'),
    path('admin/tickets/scanner/', TicketAdminScannerQRView.as_view(), name='admin-tickets-scanner'),

    path('admin/ticket_variante/<int:pk>/delete/', delete_ticket_variante, name='admin-ticket-variante-delete'),

    # URLs de los eventos (usuarios)
    path('eventos/', lambda request: redirect('eventos-listado', permanent=True), name='eventos'),
    path('eventos/listado/', EventoUserListView.as_view(), name='eventos-listado'),
    path('eventos/<int:pk>/', EventoUserDetailView.as_view(), name='eventos-detalle'),
    path('eventos/orden/', EventoUserOrderView.as_view(), name='eventos-orden'),

    # URLs para la compra de entradas de eventos.
    path('venta_ticket/', lambda request: redirect('venta-ticket-listado', permanent=True), name='venta-ticket'),
    path('venta_ticket/listado/', VentaTicketUserListView.as_view(), name='venta-ticket-listado'),
    path('venta_ticket/<int:pk>/', VentaTicketUserDetailView.as_view(), name='venta-ticket-detalle'),
    path('venta_ticket/<int:pk>/pago/', VentaTicketUserPaymentView.as_view(), name='venta-ticket-pago'),
    path('venta_ticket/checkout/', VentaTicketCheckoutView.as_view(), name='venta-ticket-checkout'),
    path('venta_ticket/<int:pk>/comprobante/', VentaTicketUserReceiptView.as_view(), name='venta-ticket-comprobante'),
    path('venta_ticket/<int:pk>/tickets/', TicketUserListView.as_view(), name='tickets-listado'),
    path('tickets/<int:pk>/', TicketUserDetailView.as_view(), name='tickets-detalle'),
]
