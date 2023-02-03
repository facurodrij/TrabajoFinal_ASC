from django.shortcuts import redirect
from django.urls import path

from eventos.views.admin.evento.views import EventoAdminListView, EventoAdminCreateView, EventoAdminUpdateView, \
    EventoAdminDeleteView
from eventos.views.user.evento.views import EventoUserDetailView, VentaTicketUserPaymentView, VentaTicketCheckoutView, \
    VentaTicketUserReceiptView, EventoUserOrderView

urlpatterns = [
    # URLs de los eventos (administración)
    path('admin/eventos/', lambda request: redirect('admin-eventos-listado', permanent=True), name='admin-eventos'),
    path('admin/eventos/listado/', EventoAdminListView.as_view(), name='admin-eventos-listado'),
    path('admin/eventos/crear/', EventoAdminCreateView.as_view(), name='admin-eventos-crear'),
    path('admin/eventos/<int:pk>/editar/', EventoAdminUpdateView.as_view(), name='admin-eventos-editar'),
    path('admin/eventos/<int:pk>/baja/', EventoAdminDeleteView.as_view(), name='admin-eventos-baja'),

    # URLs de los eventos (usuarios)
    path('eventos/<int:pk>/', EventoUserDetailView.as_view(), name='eventos-detalle'),
    path('eventos/orden/', EventoUserOrderView.as_view(), name='eventos-orden'),

    # URLs para la compra de entradas de eventos.
    path('venta_ticket/<int:pk>/pago/', VentaTicketUserPaymentView.as_view(), name='venta-ticket-pago'),
    path('venta_ticket/checkout/', VentaTicketCheckoutView.as_view(), name='venta-ticket-checkout'),
    path('venta_ticket/<int:pk>/comprobante/', VentaTicketUserReceiptView.as_view(), name='venta-ticket-comprobante'),
]
