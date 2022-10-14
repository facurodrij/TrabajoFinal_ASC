from django.contrib import admin

from .models import *

for model in [Sexo, Deporte, Superficie, Pais, Provincia, Localidad, SocioCategoria, SocioEstado]:
    admin.site.register(model)
