from datetime import datetime

import mercadopago
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView, DetailView
from num2words import num2words

from core.models import Club
from core.utilities import send_email
from eventos.models import Evento, TicketVariante, VentaTicket, Ticket, ItemVentaTicket, PagoVentaTicket
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
            tickets = []
            items = []
            total = 0
            for ticket_variante in TicketVariante.objects.filter(evento=evento):
                # Se obtiene la cantidad de tickets de la variante
                cantidad = request.POST.get(f'cantidad_{ticket_variante.pk}')
                if cantidad is None or cantidad == '0':
                    continue
                cantidad = int(cantidad)
                items.append({
                    'ticket_variante_id': ticket_variante.pk,
                    'ticket_variante': ticket_variante.nombre,
                    'cantidad': cantidad,
                    'precio_unit': ticket_variante.precio.__str__(),
                    'subtotal': (ticket_variante.precio * cantidad).__str__()
                })
                total += ticket_variante.precio * cantidad
                # Se crea un diccionario con cada ticket
                for cantidad in range(cantidad):
                    tickets.append({
                        'ticket_variante_id': ticket_variante.pk,
                        'ticket_variante': ticket_variante.__str__(),
                        'precio': ticket_variante.precio.__float__()
                    })
            if total <= 0:
                messages.error(request, 'No se ha seleccionado ningún ticket')
                return redirect('eventos-detalle', pk=evento.pk)
            # Guardar en sesión los datos de la venta
            request.session['items'] = items
            request.session['tickets'] = tickets
            request.session['total'] = float(total)
            # Redireccionar al detalle del evento con contexto de los tickets
            return render(request, 'user/evento/orden.html', {
                'title': 'Orden de Compra',
                'club_logo': Club.objects.get(pk=1).get_imagen(),
                'evento': evento,
                'tickets': tickets,
                'items': items,
                'total': str(total),
                'total_letras': 'Son: {} pesos argentinos'.format(num2words(total, lang='es'))
            })
        elif action == 'pago':
            tickets = request.session.get('tickets')
            i = 0
            for ticket in tickets:
                # Volver a armar el diccionario con los datos de los tickets ahora con el nombre de la persona
                ticket_variante = TicketVariante.objects.get(pk=ticket['ticket_variante_id'])
                tickets[i] = {
                    'ticket_variante_id': ticket_variante.pk,
                    'ticket_variante': ticket_variante.__str__(),
                    'nombre': request.POST.get(f'nombre_{ticket_variante.pk}_{i}'),
                }
                i += 1
            # Guardar en sesión los datos de la venta
            request.session['tickets'] = tickets
            return redirect('eventos-pago', pk=evento.pk)


class EventoUserPaymentView(LoginRequiredMixin, TemplateView):
    template_name = 'user/evento/payment.html'

    def get(self, request, *args, **kwargs):
        items = request.session.get('items')
        total = request.session.get('total')
        tickets = request.session.get('tickets')
        evento = Evento.objects.get(pk=kwargs['pk'])
        if items is None or tickets is None or total is None:
            messages.error(request, 'El pago del ticket no se encuentra disponible.')
            return redirect('index')
        with transaction.atomic():
            # Se crea la venta
            venta = VentaTicket.objects.create(
                email=request.user.email,
                total=total,
                pagado=False,
            )
            # Se crean los items de la venta
            for item in items:
                ItemVentaTicket.objects.create(
                    venta_ticket=venta,
                    ticket_variante_id=item['ticket_variante_id'],
                    cantidad=item['cantidad'],
                    subtotal=item['subtotal']
                )
            # Se crean los tickets
            for ticket in tickets:
                Ticket.objects.create(
                    venta_ticket=venta,
                    ticket_variante_id=ticket['ticket_variante_id'],
                    nombre=ticket['nombre'],
                    is_used=False
                )
            # Se guarda la venta en la sesión
            request.session['venta_id'] = venta.pk

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
            "expiration_date_from": venta.date_created.isoformat(),
            "expiration_date_to": venta.get_expiration_date(),
            "back_urls": {
                "success": "http://127.0.0.1:8000/eventos/{}/checkout/".format(evento.pk),
                "failure": "http://127.0.0.1:8000/eventos/{}/checkout/".format(evento.pk),
            },
            "auto_return": "approved",
            "external_reference": venta.pk
        }
        preference_result = sdk.preference().create(preference)
        preference_id = preference_result['response']['id']
        return render(request, 'user/evento/payment.html', {
            'total': total,
            'preference_id': preference_id,
            'public_key': public_key,
            'title': 'Pago de tickets',
            'club_logo': Club.objects.get(pk=1).get_imagen()})


class EventoCheckoutView(View):
    """
    Vista para obtener el pago de un evento y crear el pago en la base de datos.
    """

    def get(self, request, *args, **kwargs):
        try:
            if 'status' in request.GET:
                if request.GET['status'] == 'approved':
                    with transaction.atomic():
                        venta_ticket = VentaTicket.objects.get(pk=request.GET['external_reference'])
                        payment_info = sdk.payment().get(request.GET['payment_id'])
                        pago_venta_ticket = PagoVentaTicket.objects.create(
                            venta_ticket=venta_ticket,
                            payment_id=request.GET['payment_id'],
                            status=payment_info['response']['status'],
                            status_detail=payment_info['response']['status_detail'],
                            transaction_amount=payment_info['response']['transaction_amount'],
                            date_approved=payment_info['response']['date_approved'],
                        )
                        venta_ticket.pagado = True
                        venta_ticket.save()
                        subject = 'Compra de tickets - Pago Aprobado'
                        template = 'email/payment_approved.html'
                        context = {
                            'venta_ticket': venta_ticket,
                            'pago_venta_ticket': pago_venta_ticket,
                            'protocol': 'https' if request.is_secure() else 'http',
                            'domain': get_current_site(request)
                        }
                        send_email(subject, template, context, venta_ticket.email)
                        messages.success(request, 'El pago se ha realizado correctamente. '
                                                  'Se ha enviado un correo de confirmación.')
                    return redirect('index')
                else:
                    messages.error(request, 'Error al realizar el pago.')
                    return redirect('index')
            else:
                messages.error(request, 'Error al realizar el pago.')
                return redirect('index')
        except Exception as e:
            messages.error(request, 'Error al realizar el pago.')
            return redirect('index')


class VentaTicketUserReceiptView(TemplateView):
    """
    Vista para obtener el comprobante de pago de una venta de tickets.
    """
    template_name = 'user/evento/receipt.html'

    def get(self, request, *args, **kwargs):
        try:
            venta_ticket = VentaTicket.objects.get(pk=kwargs['pk'])
            pago_venta_ticket = PagoVentaTicket.objects.get(venta_ticket=venta_ticket)
            if venta_ticket.pagado:
                return render(request, 'user/evento/receipt.html', {
                    'title': 'Comprobante de Pago',
                    'club': Club.objects.get(pk=1),
                    'venta_ticket': venta_ticket,
                    'pago_venta_ticket': pago_venta_ticket,
                    'fecha_actual': datetime.now()
                })
            else:
                messages.error(request, 'El comprobante de pago no se encuentra disponible.')
                return redirect('index')
        except (VentaTicket.DoesNotExist, PagoVentaTicket.DoesNotExist):
            messages.error(request, 'El comprobante de pago no se encuentra disponible.')
            return redirect('index')
