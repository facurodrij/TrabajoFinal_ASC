from django.contrib import admin

from core.models import Club, Cancha, HoraLaboral, CanchaHoraLaboral, Reserva

for model in [Club, Cancha, HoraLaboral, CanchaHoraLaboral, Reserva]:
    admin.site.register(model)
