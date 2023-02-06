from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView

from core.models import Club
from eventos.models import Ticket, send_qr_code


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
                    ticket.check_date = datetime.now()
                    ticket.check_by = request.user
                else:
                    ticket.is_used = False
                    ticket.check_date = None
                    ticket.check_by = None
                ticket.save()
            elif action == 'is_used_change_lote':
                ids = request.POST.getlist('ids[]')
                tickets = Ticket.objects.filter(pk__in=ids)
                tickets.update(is_used=True, check_date=datetime.now(), check_by=request.user)
            elif action == 'delete_lote':
                change_reason = request.POST['change_reason']
                ids = request.POST.getlist('ids[]')
                tickets = Ticket.objects.filter(pk__in=ids)
                for ticket in tickets:
                    ticket._change_reason = change_reason
                tickets.delete()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = e.args[0]
        return JsonResponse(data)


class TicketAdminDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Ticket
    template_name = 'admin/ticket/detail.html'
    context_object_name = 'ticket'
    permission_required = 'eventos.view_ticket'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle del Ticket'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            email = request.POST['email']
            if action == 'send_qr':
                ticket = Ticket.objects.filter(pk=self.kwargs['pk']).first()
                if ticket:
                    send_qr_code([ticket.pk], email)
                messages.success(request, 'El código QR se ha enviado correctamente')
                return redirect('admin-tickets-detalle', pk=self.kwargs['pk'])
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = e.args[0]
        messages.error(request, data['error'])
        return redirect('admin-tickets-detalle', pk=self.kwargs['pk'])


class TicketAdminScannerQRView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'admin/ticket/scanner_qr.html'
    permission_required = 'eventos.change_ticket'

    # TODO: Personalizar el template

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Escanear Código QR'
        return context


class TicketAdminQRView(LoginRequiredMixin, PermissionRequiredMixin, View):
    context_object_name = 'ticket'
    permission_required = 'eventos.change_ticket'

    def get(self, request, *args, **kwargs):
        try:
            ticket = Ticket.objects.get(pk=self.kwargs['pk'])
            venta_ticket = ticket.venta_ticket
            if not venta_ticket.pagado:
                raise ValueError('El ticket no ha sido pagado')
            if not ticket.is_used:
                with transaction.atomic():
                    ticket.is_used = True
                    ticket.check_date = datetime.now()
                    ticket.check_by = request.user
                    ticket.save()
                return render(request, 'admin/ticket/qr.html', {
                    'title': 'Código QR del Ticket',
                    'ticket': ticket,
                    'icon': 'success',
                    'success': True})
            else:
                return render(request, 'admin/ticket/qr.html', {
                    'title': 'Código QR del Ticket',
                    'ticket': ticket,
                    'icon': 'error',
                    'error': 'is_used',
                    'check_date': ticket.check_date,
                    'check_by': ticket.check_by,
                    'text': 'El ticket ya ha sido usado',
                    'success': False})
        except Ticket.DoesNotExist:
            return render(request, 'admin/ticket/qr.html', {
                'title': 'Código QR del Ticket',
                'ticket': None,
                'icon': 'error',
                'error': 'El ticket no existe o el código QR no es válido',
                'success': False
            })
        except ValueError as e:
            return render(request, 'admin/ticket/qr.html', {
                'title': 'Código QR del Ticket',
                'ticket': None,
                'icon': 'error',
                'error': e.args[0],
                'success': False
            })
