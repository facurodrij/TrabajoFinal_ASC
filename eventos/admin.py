from django.contrib import admin

from eventos.models import Evento, Parameters, VentaTicket, ItemVentaTicket, Ticket

for model in [Evento, Parameters, VentaTicket, ItemVentaTicket, Ticket]:
    admin.site.register(model)
