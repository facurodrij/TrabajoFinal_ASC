from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from core.models import Club


class ClubAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return Club.global_objects.all()


admin.site.register(Club, ClubAdmin)
