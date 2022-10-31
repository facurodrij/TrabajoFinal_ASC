from django.contrib import admin

from .models import *

models = [Socio, Miembro, Categoria, Estado]

for model in models:
    admin.site.register(model)
