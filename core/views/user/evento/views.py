from datetime import datetime

import mercadopago
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import PasswordResetConfirmView, INTERNAL_RESET_SESSION_TOKEN
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db import transaction
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import ListView, TemplateView, CreateView, DeleteView, DetailView, FormView

from accounts.views import User
from core.models import Club, Evento, VentaTicket, DetalleVentaTicket, Ticket, TicketVariante
from static.credentials import MercadoPagoCredentials  # Aquí debería insertar sus credenciales de MercadoPago

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)


class EventoUserDetailView(DetailView):
    """
    Vista para mostrar los detalles de una reserva.
    """
    model = Evento
    template_name = 'user/evento/detail.html'
    context_object_name = 'evento'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle del Evento'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        context['ticket_variante_list'] = TicketVariante.objects.filter(evento=self.object)
        return context

    def post(self, request, *args, **kwargs):
        evento = self.get_object()
        action = request.POST.get('action')
        if action == 'orden':
            # La vista puede enviar varias variantes de tickets y la cantidad de cada una, por lo que se
            # debe iterar sobre cada una de ellas.
            items = []
            total = 0
            # for ticket_variante in request.POST.getlist('ticket_variante'):
            for ticket_variante in TicketVariante.objects.filter(evento=evento):
                # Se obtiene la cantidad de tickets de la variante
                cantidad = request.POST.get(f'cantidad_{ticket_variante.pk}')
                if cantidad is None or cantidad == '0':
                    continue
                cantidad = int(cantidad)
                # Guardar en un diccionario la variante de ticket y la cantidad
                items.append({
                    'ticket_variante_id': ticket_variante.pk,
                    'ticket_variante': ticket_variante.__str__(),
                    'cantidad': cantidad,
                    'subtotal': str(ticket_variante.precio * cantidad),
                })
                # Calcular el total
                total += ticket_variante.precio * cantidad
            if total <= 0:
                messages.error(request, 'No se ha seleccionado ningún ticket')
                return redirect('eventos-detalle', pk=evento.pk)
            # Guardar en sesión los datos de la venta
            request.session['items'] = items
            request.session['total'] = float(total)
            # Redireccionar al detalle del evento con contexto de los tickets
            return render(request, 'user/evento/orden.html', {
                'evento': evento,
                'items': items,
                'total': str(total),
                'title': 'Orden de Compra',
                'club_logo': Club.objects.get(pk=1).get_imagen()})
        elif action == 'pago':
            return redirect('eventos-pago', pk=evento.pk)

    # TODO: Implementar vista para que el usuario pueda ver la venta y pagarla


class EventoUserPaymentView(LoginRequiredMixin, TemplateView):
    template_name = 'user/evento/payment.html'

    def get(self, request, *args, **kwargs):
        items = request.session.get('items')
        total = request.session.get('total')
        evento = Evento.objects.get(pk=kwargs['pk'])
        if items is None:
            messages.error(request, 'El pago del ticket no se encuentra disponible.')
            return redirect('index')
        # Se crea el pago en MercadoPago
        preference = {
            "items": [
                {
                    "title": "Compra de tickets",
                    "quantity": 1,
                    "currency_id": "ARS",
                    "unit_price": float(total)
                }
            ],
            "payer": {
                "name": request.user.nombre,
                "email": request.user.email
            },
            "statement_descriptor": "Compra de tickets",
            "excluded_payment_types": [
                {
                    "id": "ticket"
                }
            ],
            "installments": 1,
            "binary_mode": True,
            "expires": True,
            "expiration_date_from": evento.date_created.isoformat(),
            "expiration_date_to": evento.get_expiration_date(),
            "back_urls": {
                "success": "http://127.0.0.1:8000/eventos/{}/checkout/".format(evento.pk),
                "failure": "http://127.0.0.1:8000/eventos/{}/checkout/".format(evento.pk),
            },
            "auto_return": "approved",
        }
        preference_result = sdk.preference().create(preference)
        preference_id = preference_result['response']['id']
        return render(request, 'user/evento/payment.html', {
            'items': items,
            'total': total,
            'preference_id': preference_id,
            'public_key': public_key,
            'title': 'Pago de tickets',
            'club_logo': Club.objects.get(pk=1).get_imagen()})


class EventoCheckoutView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        items = request.session.get('items')
        total = request.session.get('total')
        evento = Evento.objects.get(pk=kwargs['pk'])
        if items is None:
            messages.error(request, 'El pago del ticket no se encuentra disponible.')
            return redirect('index')
        if 'status' in request.GET:
            if request.GET['status'] == 'approved':
                with transaction.atomic():
                    venta_ticket = VentaTicket.objects.create(
                        email=request.user.email,
                        total=total,
                        preference_id=request.GET['preference_id'],
                        pagado=True,
                    )
                    for item in items:
                        ticket_variante = TicketVariante.objects.get(pk=item['ticket_variante_id'])
                        detalle_venta_ticket = DetalleVentaTicket.objects.create(
                            ticket_variante=ticket_variante,
                            venta_ticket=venta_ticket,
                            cantidad=item['cantidad'],
                            subtotal=ticket_variante.precio * item['cantidad']
                        )
                    venta_ticket.save()
                    messages.success(request, 'El pago se ha realizado correctamente.')
                    # TODO: Generar ticket y enviar qr por mail
                return redirect('index')
        else:
            messages.error(request, 'Error al realizar el pago.')
            return redirect('index')
