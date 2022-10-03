from django.contrib import admin

from .models import *

for model in [Club, Cancha, Socio]:
    admin.site.register(model)
