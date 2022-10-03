from django.contrib import admin

from .models import *

for model in [Genero, Deporte, Superficie, Pais, Provincia, Localidad, SocioCategoria, SocioEstado]:
    admin.site.register(model)
