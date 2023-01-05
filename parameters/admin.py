from django.contrib import admin

from parameters.models import Sexo, Pais, Provincia, Localidad, Departamento, Municipio, Deporte, Superficie

for model in [Sexo, Pais, Provincia, Localidad, Departamento, Municipio, Deporte, Superficie]:
    admin.site.register(model)
