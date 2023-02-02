from django.contrib import admin

from reservas.models import Cancha, HoraLaboral, CanchaHoraLaboral, Reserva, Deporte, Superficie, Parameters

for model in [Cancha, HoraLaboral, CanchaHoraLaboral, Reserva, Deporte, Superficie, Parameters]:
    admin.site.register(model)
