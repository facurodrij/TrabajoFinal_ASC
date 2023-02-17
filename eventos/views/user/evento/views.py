from datetime import datetime

import mercadopago
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView, DetailView, ListView
from num2words import num2words

from core.models import Club
from core.utilities import send_email
from eventos.models import Evento, TicketVariante, VentaTicket, Ticket, ItemVentaTicket, PagoVentaTicket, Parameters, \
    send_qr_code
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
            ticket_variantes = TicketVariante.objects.filter(evento=evento)
            venta_tickets = VentaTicket.objects.filter(itemventaticket__ticket_variante__in=ticket_variantes)
            for venta_ticket in venta_tickets:
                venta_ticket.clean()
        except (TicketVariante.DoesNotExist, VentaTicket.DoesNotExist, ValidationError):
            pass
        if evento.get_expiration_date(isoformat=False) < datetime.now().date():
            messages.error(request, 'El evento ya no se encuentra disponible para la compra de tickets')
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
        try:
            action = request.POST.get('action')
            if action == 'orden':
                tickets = []
                items = []
                subtotal = 0
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
                        messages.error(request,
                                       'No hay suficientes tickets {} disponibles'.format(ticket_variante.nombre))
                        return redirect('eventos-detalle', pk=evento.pk)
                    items.append({
                        'ticket_variante_id': ticket_variante.pk,
                        'ticket_variante': ticket_variante.nombre,
                        'cantidad': cantidad,
                        'precio_unit': ticket_variante.precio.__float__(),
                        'subtotal': (ticket_variante.precio * cantidad).__float__()
                    })
                    subtotal += ticket_variante.precio * cantidad
                    # Se crea un diccionario con cada ticket
                    for cantidad in range(cantidad):
                        tickets.append({
                            'ticket_variante_id': ticket_variante.pk,
                            'ticket_variante': ticket_variante.__str__(),
                            'precio': ticket_variante.precio.__float__()
                        })
                if subtotal <= 0:
                    messages.error(request, 'No se ha seleccionado ningún ticket')
                    return redirect('eventos-detalle', pk=evento.pk)
                if cantidad_tickets > max_tickets_por_venta:
                    messages.error(request, 'No se pueden comprar más de {} tickets'.format(max_tickets_por_venta))
                    return redirect('eventos-detalle', pk=evento.pk)
                # Guardar en sesión los datos de la venta
                # Si el usuario está logueado, y es socio, se le aplica el descuento
                if request.user.is_authenticated and request.user.get_socio():
                    request.session['descuento_socio'] = float(evento.descuento_socio)
                request.session['items'] = items
                request.session['tickets'] = tickets
                request.session['subtotal'] = float(subtotal)
                request.session['evento_id'] = evento.pk
                return redirect('eventos-orden')
        except Exception as e:
            messages.error(request, 'Ha ocurrido un error al procesar la solicitud')
            return redirect('eventos-detalle', pk=evento.pk)


class EventoUserOrderView(TemplateView):
    template_name = 'user/evento/orden.html'

    def dispatch(self, request, *args, **kwargs):
        try:
            evento = Evento.objects.get(pk=request.session['evento_id'])
        except (Evento.DoesNotExist, KeyError):
            messages.error(request, 'No se ha seleccionado ningún evento')
            return redirect('index')
        try:
            ticket_variantes = TicketVariante.objects.filter(evento=evento)
            venta_tickets = VentaTicket.objects.filter(itemventaticket__ticket_variante__in=ticket_variantes)
            for venta_ticket in venta_tickets:
                venta_ticket.clean()
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
        descuento_socio = self.request.session.get('descuento_socio') or 0
        subtotal = self.request.session.get('subtotal')
        total = subtotal - (subtotal * descuento_socio)
        context = super().get_context_data(**kwargs)
        context['title'] = 'Orden de Compra'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        context['evento'] = evento
        context['tickets'] = tickets
        context['items'] = items
        context['descuento_socio'] = descuento_socio * 100
        context['descuento_valor'] = float(subtotal * descuento_socio)
        context['subtotal'] = float(subtotal)
        context['total'] = float(total)
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
            descuento_socio = request.session.get('descuento_socio') or 0
            subtotal = request.session.get('subtotal')
            if items is None or tickets is None or subtotal is None:
                messages.error(request, 'No se ha seleccionado ningún ticket')
                return redirect('eventos-detalle', pk=evento.pk)
            i = 0
            for ticket in tickets:
                # Volver a armar el diccionario con los datos de los tickets ahora con el nombre de la persona
                ticket_variante = TicketVariante.objects.get(pk=ticket['ticket_variante_id'])
                tickets[i] = {
                    'ticket_variante_id': ticket_variante.pk,
                    'ticket_variante': ticket_variante.__str__(),
                    'dni': request.POST.get(f'dni_{ticket_variante.pk}_{i}'),
                    'nombre': request.POST.get(f'nombre_{ticket_variante.pk}_{i}'),
                }
                i += 1
            try:
                with transaction.atomic():
                    # Se crea la venta
                    email = request.POST.get('email')
                    venta = VentaTicket.objects.create(
                        evento=evento,
                        email=email,
                        subtotal=subtotal,
                        porcentaje_descuento=descuento_socio * 100,
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
                            dni=ticket['dni'],
                            nombre=ticket['nombre'],
                            is_used=False
                        )
                    # Enviar correo con el link de pago.
                    subject = 'Compra de Tickets - Pago Pendiente'
                    template = 'email/evento_payment_link.html'
                    context = {'venta': venta,
                               'items': venta.itemventaticket_set.all(),
                               'tickets': venta.ticket_set.all(),
                               'protocol': 'https' if self.request.is_secure() else 'http',
                               'domain': get_current_site(request)}
                    send_email(subject, template, context, venta.email)
                    messages.success(request, 'Se ha enviado un correo electrónico con el link de pago.')
            except (IntegrityError, ValidationError, Exception) as e:
                messages.error(request, 'No se ha podido crear la venta, error: {}'.format(e))
                return redirect('eventos-orden')
            return redirect('venta-ticket-pago', pk=venta.pk)


class VentaTicketUserPaymentView(TemplateView):
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
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        venta_ticket = VentaTicket.objects.get(pk=kwargs['pk'])
        preference_id = venta_ticket.preference_id
        site = get_current_site(request)
        complete_url = '{}://{}{}'.format('https' if self.request.is_secure() else 'http', site.domain,
                                          reverse('venta-ticket-checkout'))
        if preference_id is None:
            # Se crea el pago en MercadoPago
            preference = {
                "items": [
                    {
                        "title": "Compra de tickets",
                        "quantity": 1,
                        "currency_id": "ARS",
                        "unit_price": float(venta_ticket.total())
                    }
                ],
                "payer": {
                    "email": venta_ticket.email
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
                    "success": "{}://{}{}".format('https' if self.request.is_secure() else 'http', site.domain,
                                                  reverse('venta-ticket-checkout')),
                    "failure": "{}://{}{}".format('https' if self.request.is_secure() else 'http', site.domain,
                                                  reverse('venta-ticket-checkout'))
                },
                "auto_return": "approved",
                "external_reference": venta_ticket.pk
            }
            preference_result = sdk.preference().create(preference)
            preference_id = preference_result['response']['id']
            venta_ticket.preference_id = preference_id
            venta_ticket.save()
        return render(request, 'user/evento/payment.html', {
            'venta_ticket': venta_ticket,
            'items': venta_ticket.itemventaticket_set.all(),
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
                    send_email(subject, template, context, venta_ticket.email, True)
                    tickets = venta_ticket.ticket_set.all()
                    ids = [ticket.id for ticket in tickets]
                    send_qr_code(ids, venta_ticket.email)
                    messages.success(request, 'El pago se ha realizado correctamente. '
                                              'Se ha enviado un correo de confirmación con los tickets adquiridos.')
                    return redirect('index')
                else:
                    messages.error(request, 'Error al realizar el pago.')
                    return redirect('index')
            else:
                messages.error(request, 'Error al realizar el pago.')
                return redirect('index')
        except Exception as e:
            print('VentaTicketCheckoutView: ', e.args[0])
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


class VentaTicketUserListView(LoginRequiredMixin, ListView):
    model = VentaTicket
    template_name = 'user/venta_ticket/list.html'
    context_object_name = 'ventas'

    def get_queryset(self):
        return VentaTicket.objects.filter(email=self.request.user.email).order_by('-date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mis Pedidos'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context


class VentaTicketUserDetailView(LoginRequiredMixin, DetailView):
    model = VentaTicket
    template_name = 'user/venta_ticket/detail.html'
    context_object_name = 'venta_ticket'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle del Pedido'
        context['items'] = self.object.itemventaticket_set.all()
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context


class TicketUserListView(LoginRequiredMixin, ListView):
    """
    Vista para obtener los tickets de un usuario.
    """
    model = Ticket
    template_name = 'user/ticket/list.html'
    context_object_name = 'tickets'

    def get(self, request, *args, **kwargs):
        try:
            venta_ticket = VentaTicket.objects.get(pk=self.kwargs['pk'], email=self.request.user.email)
            if not venta_ticket.pagado:
                messages.error(self.request, 'Los tickets no se encuentran disponibles.')
                return redirect('venta-ticket-detalle', pk=venta_ticket.pk)
        except VentaTicket.DoesNotExist:
            messages.error(self.request, 'Los tickets no se encuentran disponibles.')
            return redirect('index')
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        venta_ticket = VentaTicket.objects.get(pk=self.kwargs['pk'], email=self.request.user.email)
        return venta_ticket.ticket_set.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Tickets Adquiridos'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context


class TicketUserDetailView(LoginRequiredMixin, DetailView):
    """
    Vista para obtener el detalle de un ticket.
    """
    model = Ticket
    template_name = 'user/ticket/detail.html'
    context_object_name = 'ticket'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle del Ticket'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context


class EventoUserListView(LoginRequiredMixin, ListView):
    """
    Vista para obtener los eventos de un usuario.
    """
    model = Evento
    template_name = 'user/evento/list.html'
    context_object_name = 'eventos'

    def get_queryset(self):
        return Evento.objects.filter(fecha_inicio__gte=datetime.now().date()).order_by('fecha_inicio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eventos'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context
