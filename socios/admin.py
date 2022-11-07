from django.contrib import admin

from .models import *

models = [Categoria, Estado]

for model in models:
    admin.site.register(model)
