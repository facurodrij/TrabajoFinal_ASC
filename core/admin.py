from django.contrib import admin

from core.models import *

for model in [Club]:
    admin.site.register(model)
