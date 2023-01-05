from django.contrib import admin

from core.models import Club, Cancha, HoraLaboral, CanchaHoraLaboral

for model in [Club, Cancha, HoraLaboral, CanchaHoraLaboral]:
    admin.site.register(model)
