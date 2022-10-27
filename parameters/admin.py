from django.contrib import admin

from .models import *

for model in [Parentesco, Sexo, Pais, Provincia, Localidad]:
    admin.site.register(model)
