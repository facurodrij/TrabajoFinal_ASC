from django.contrib import admin

from .models import *

models = [SocioIndividual, GrupoFamiliar, MiembroRegistrado, MiembroNoRegistrado, Categoria, Tipo, Estado]

for model in models:
    admin.site.register(model)
