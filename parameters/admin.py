from django.contrib import admin

from parameters.models import *

for model in [Sexo, Pais, Provincia, Localidad, Departamento, Municipio, Deporte, Superficie, ReservaParameters]:
    admin.site.register(model)
