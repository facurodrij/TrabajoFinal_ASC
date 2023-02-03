from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.views.generic import ListView

from eventos.models import Ticket


class TicketAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Ticket
    template_name = 'admin/ticket/list.html'
    context_object_name = 'tickets'
    permission_required = 'eventos.view_ticket'

    def get_queryset(self):
        return Ticket.objects.all().values('id', 'ticket_variante__evento__nombre', 'ticket_variante__nombre', 'nombre',
                                           'is_used')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Tickets'
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'is_used_change':
                ticket = Ticket.objects.get(pk=request.POST['ticket_id'])
                usado = request.POST['usado']
                if usado == 'true':
                    ticket.is_used = True
                else:
                    ticket.is_used = False
                ticket.save()
            elif action == 'is_used_change_lote':
                ids = request.POST.getlist('ids[]')
                tickets = Ticket.objects.filter(pk__in=ids)
                tickets.update(is_used=True)
            elif action == 'delete_lote':
                ids = request.POST.getlist('ids[]')
                tickets = Ticket.objects.filter(pk__in=ids)
                tickets.delete()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = e.args[0]
        return JsonResponse(data)
