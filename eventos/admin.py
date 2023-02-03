from django.contrib import admin

from eventos.models import Evento, Parameters, VentaTicket

for model in [Evento, Parameters, VentaTicket]:
    admin.site.register(model)
