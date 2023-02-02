from django.contrib import admin

from reservas.models import Cancha, HoraLaboral, CanchaHoraLaboral, Reserva, Deporte, Superficie

for model in [Cancha, HoraLaboral, CanchaHoraLaboral, Reserva, Deporte, Superficie]:
    admin.site.register(model)
