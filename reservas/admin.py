from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from reservas.models import *


class ReservaAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return Reserva.global_objects.all()


class CanchaAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return Cancha.global_objects.all()


admin.site.register(Parameters, SimpleHistoryAdmin)
admin.site.register(Reserva, ReservaAdmin)
admin.site.register(PagoReserva, SimpleHistoryAdmin)
admin.site.register(Cancha, CanchaAdmin)
admin.site.register(CanchaHoraLaboral)
admin.site.register(HoraLaboral)
admin.site.register(Deporte)
admin.site.register(Superficie)
