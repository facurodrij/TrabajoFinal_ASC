from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from socios.models import *


class SocioAdmin(SimpleHistoryAdmin):

    def get_queryset(self, request):
        return Socio.global_objects.all()


class CuotaSocialAdmin(SimpleHistoryAdmin):

    def get_queryset(self, request):
        return CuotaSocial.global_objects.all()


class PagoCuotaSocialAdmin(SimpleHistoryAdmin):

    def get_queryset(self, request):
        return PagoCuotaSocial.global_objects.all()


admin.site.register(Parameters, SimpleHistoryAdmin)
admin.site.register(Socio, SocioAdmin)
admin.site.register(Categoria, SimpleHistoryAdmin)
admin.site.register(CuotaSocial, CuotaSocialAdmin)
admin.site.register(ItemCuotaSocial, SimpleHistoryAdmin)
admin.site.register(PagoCuotaSocial, PagoCuotaSocialAdmin)
