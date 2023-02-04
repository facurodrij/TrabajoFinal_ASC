from datetime import datetime

import mercadopago
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView, DetailView
from num2words import num2words

from core.models import Club
from core.utilities import send_email
from eventos.models import Evento, TicketVariante, VentaTicket, Ticket, ItemVentaTicket, PagoVentaTicket, Parameters
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

    def dispatch(self, request, *args, **kwargs):
        evento = self.get_object()
        try:
            ticket_variante = TicketVariante.objects.get(evento=evento)
            for item in ticket_variante.itemventaticket_set.filter(venta_ticket__is_deleted=False,
                                                                   venta_ticket__pagado=False):
                item.venta_ticket.clean()
        except (TicketVariante.DoesNotExist, VentaTicket.DoesNotExist, ValidationError):
            pass
        if evento.get_expiration_date(isoformat=False) < datetime.now().date():
            messages.error(request, 'El evento ya ha expirado.')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)

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
            max_tickets_por_venta = Parameters.objects.get(pk=1).max_tickets_por_venta
            cantidad_tickets = 0
            for ticket_variante in TicketVariante.objects.filter(evento=evento):
                # Se obtiene la cantidad de tickets de la variante
                cantidad = request.POST.get(f'cantidad_{ticket_variante.pk}')
                if cantidad is None or cantidad == '0':
                    continue
                cantidad = int(cantidad)
                cantidad_tickets += cantidad
                if cantidad > ticket_variante.get_tickets_restantes():
                    messages.error(request, 'No hay suficientes tickets {} disponibles'.format(ticket_variante.nombre))
                    return redirect('eventos-detalle', pk=evento.pk)
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
            if cantidad_tickets > max_tickets_por_venta:
                messages.error(request, 'No se pueden comprar más de {} tickets'.format(max_tickets_por_venta))
                return redirect('eventos-detalle', pk=evento.pk)
            # Guardar en sesión los datos de la venta
            request.session['items'] = items
            request.session['tickets'] = tickets
            request.session['total'] = float(total)
            request.session['evento_id'] = evento.pk
            return redirect('eventos-orden')


class EventoUserOrderView(LoginRequiredMixin, TemplateView):
    template_name = 'user/evento/orden.html'

    def dispatch(self, request, *args, **kwargs):
        try:
            evento = Evento.objects.get(pk=request.session['evento_id'])
        except (Evento.DoesNotExist, KeyError):
            messages.error(request, 'No se ha seleccionado ningún evento')
            return redirect('index')
        try:
            ticket_variante = TicketVariante.objects.get(evento=evento)
            for item in ticket_variante.itemventaticket_set.filter(venta_ticket__is_deleted=False,
                                                                   venta_ticket__pagado=False):
                item.venta_ticket.clean()
        except (TicketVariante.DoesNotExist, VentaTicket.DoesNotExist, ValidationError):
            pass
        if evento.get_expiration_date(isoformat=False) < datetime.now().date():
            messages.error(request, 'El evento ya ha expirado.')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        evento = Evento.objects.get(pk=self.request.session['evento_id'])
        tickets = self.request.session.get('tickets')
        items = self.request.session.get('items')
        total = self.request.session.get('total')
        context = super().get_context_data(**kwargs)
        context['title'] = 'Orden de Compra'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        context['evento'] = evento
        context['tickets'] = tickets
        context['items'] = items
        context['total'] = str(total)
        context['total_letras'] = 'Son: {} pesos argentinos'.format(num2words(total, lang='es'))
        return context

    def post(self, request, *args, **kwargs):
        try:
            evento = Evento.objects.get(pk=request.session['evento_id'])
        except (Evento.DoesNotExist, KeyError):
            messages.error(request, 'No se ha seleccionado ningún evento')
            return redirect('index')
        action = request.POST.get('action')
        if action == 'pago':
            items = request.session.get('items')
            tickets = request.session.get('tickets')
            total = request.session.get('total')
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
            with transaction.atomic():
                # Se crea la venta
                venta = VentaTicket.objects.create(
                    user=request.user,
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
            return redirect('venta-ticket-pago', pk=venta.pk)


class VentaTicketUserPaymentView(LoginRequiredMixin, TemplateView):
    template_name = 'user/evento/payment.html'

    def dispatch(self, request, *args, **kwargs):
        # Obtener el evento mediante kwargs
        venta_ticket = VentaTicket.objects.get(pk=kwargs['pk'])
        try:
            venta_ticket.clean()
        except ValidationError as e:
            messages.error(request, e.args[0])
            return redirect('index')
        if venta_ticket.pagado:
            messages.error(request, 'El pago del ticket ya se encuentra realizado.')
            return redirect('index')  # TODO: Redireccionar a la página de tickets
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        venta_ticket = VentaTicket.objects.get(pk=kwargs['pk'])
        preference_id = venta_ticket.preference_id
        if preference_id is None:
            # Se crea el pago en MercadoPago
            preference = {
                "items": [
                    {
                        "title": "Compra de tickets",
                        "quantity": 1,
                        "currency_id": "ARS",
                        "unit_price": float(venta_ticket.total)
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
                "expiration_date_from": venta_ticket.date_created.isoformat(),
                "expiration_date_to": venta_ticket.get_expiration_date(),
                "back_urls": {
                    "success": "http://127.0.0.1:8000/venta_ticket/checkout/".format(venta_ticket.pk),
                    "failure": "http://127.0.0.1:8000/venta_ticket/checkout/".format(venta_ticket.pk),
                },
                "auto_return": "approved",
                "external_reference": venta_ticket.pk
            }
            preference_result = sdk.preference().create(preference)
            preference_id = preference_result['response']['id']
            venta_ticket.preference_id = preference_id
            venta_ticket.save()
        return render(request, 'user/evento/payment.html', {
            'preference_id': preference_id,
            'public_key': public_key,
            'title': 'Pago de tickets',
            'club_logo': Club.objects.get(pk=1).get_imagen()})


class VentaTicketCheckoutView(View):
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
                        template = 'email/evento_payment_approved.html'
                        context = {
                            'venta_ticket': venta_ticket,
                            'pago_venta_ticket': pago_venta_ticket,
                            'protocol': 'https' if request.is_secure() else 'http',
                            'domain': get_current_site(request)
                        }
                        send_email(subject, template, context, venta_ticket.user.email, True)
                        messages.success(request, 'El pago se ha realizado correctamente. '
                                                  'Se ha enviado un correo de confirmación.')
                        # TODO: Enviar QR del ticket con la url de detalle del ticket
                    return redirect('index')
                else:
                    messages.error(request, 'Error al realizar el pago.')
                    return redirect('index')
            else:
                messages.error(request, 'Error al realizar el pago.')
                return redirect('index')
        except Exception as e:
            print(e)
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
                    'items_venta_ticket': venta_ticket.itemventaticket_set.all(),
                    'pago_venta_ticket': pago_venta_ticket,
                    'transaction_amount_letras': 'Son: {} pesos argentinos'.format(
                        num2words(pago_venta_ticket.transaction_amount, lang='es')),
                    'fecha_actual': datetime.now()
                })
            else:
                messages.error(request, 'El comprobante de pago no se encuentra disponible.')
                return redirect('index')
        except (VentaTicket.DoesNotExist, PagoVentaTicket.DoesNotExist):
            messages.error(request, 'El comprobante de pago no se encuentra disponible.')
            return redirect('index')
