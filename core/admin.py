from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from core.models import Club, Persona


class ClubAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return Club.global_objects.all()


class PersonaAdmin(SimpleHistoryAdmin):
    """
    Formulario para registrar una nueva persona desde el panel de administrador.
    """
    # La lista deben ser los campos que se muestran en la tabla de personas
    list_display = ("cuil", "nombre", "apellido", "is_deleted")

    def get_queryset(self, request):
        return Persona.global_objects.all()


admin.site.register(Club, ClubAdmin)
admin.site.register(Persona, PersonaAdmin)
