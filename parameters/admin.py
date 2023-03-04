from django.contrib import admin

from parameters.models import *

for model in [Sexo, Pais, Provincia, Localidad, Departamento, Municipio, MedioPago]:
    admin.site.register(model)
