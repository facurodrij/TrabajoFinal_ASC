from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from socios.models import Socio


class SocioAdmin(SimpleHistoryAdmin):
    """
    Formulario para registrar una nueva persona desde el panel de administrador.
    """

    def get_queryset(self, request):
        return Socio.global_objects.all()


admin.site.register(Socio, SocioAdmin)
