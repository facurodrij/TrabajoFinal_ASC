from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from eventos.models import *


class EventoAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return Evento.global_objects.all()


class TicketVarianteAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return TicketVariante.global_objects.all()


class TicketAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return Ticket.global_objects.all()


class VentaTicketAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return VentaTicket.global_objects.all()


class ItemVentaTicketAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return ItemVentaTicket.objects.all()


class PagoVentaTicketAdmin(SimpleHistoryAdmin):
    def get_queryset(self, request):
        return PagoVentaTicket.objects.all()


admin.site.register(Evento, EventoAdmin)
admin.site.register(TicketVariante, TicketVarianteAdmin)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(VentaTicket, VentaTicketAdmin)
admin.site.register(ItemVentaTicket, ItemVentaTicketAdmin)
admin.site.register(PagoVentaTicket, PagoVentaTicketAdmin)
