from django.contrib import admin

from core.models import Club, Cancha, HoraLaboral, CanchaHoraLaboral, Reserva, PagoReserva

for model in [Club, Cancha, HoraLaboral, CanchaHoraLaboral, Reserva, PagoReserva]:
    admin.site.register(model)
