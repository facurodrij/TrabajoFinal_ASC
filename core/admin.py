from django.contrib import admin

from .models import *

for model in [Club, Cancha]:
    admin.site.register(model)
