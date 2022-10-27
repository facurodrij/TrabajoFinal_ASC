from django.contrib import admin

from .models import *

for model in [Club]:
    admin.site.register(model)
