from datetime import datetime, timedelta, time

import mercadopago
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.generic import ListView, TemplateView, CreateView, DeleteView, DetailView
from num2words import num2words

from accounts.views import User
from core.models import Club
from core.utilities import send_email
from reservas.forms import ReservaUserForm
from reservas.models import Reserva, PagoReserva, Cancha, HoraLaboral, Parameters
from reservas.tokens import reserva_create_token
from static.credentials import MercadoPagoCredentials  # Aquí debería insertar sus credenciales de MercadoPago

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)

UserModel = get_user_model()


class ReservaUserCreateView(CreateView):
    """
    Vista para obtener canchas disponibles en una fecha y hora determinada.
    """
    model = Reserva
    template_name = 'user/reserva/form.html'
    form_class = ReservaUserForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        try:
            form.fields['deporte'].initial = self.request.GET['deporte']
            form.fields['fecha'].initial = self.request.GET['fecha']
            form.fields['hora'].initial = self.request.GET['hora']
        except KeyError:
            form.fields['fecha'].initial = datetime.now().date()
        # Si el usuario está autenticado completa el campo email y nombre con los datos del usuario
        if self.request.user.is_authenticated:
            form.fields['email'].initial = self.request.user.email
            form.fields['nombre'].initial = self.request.user.get_full_name()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reservar Cancha'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'detail':
                form = self.form_class(request.POST)
                if form.is_valid():
                    with transaction.atomic():
                        reserva = form.save(commit=False)
                        data['reserva'] = reserva.toJSON()
                else:
                    data['error'] = form.errors
            elif action == 'add':
                form = self.form_class(request.POST)
                if form.is_valid():
                    with transaction.atomic():
                        reserva = form.save()
                        # Enviar correo con el link de pago.
                        subject = 'Reserva de Cancha - Pago Pendiente'
                        template = 'email/reserva_payment_link.html'
                        context = {'reserva': reserva,
                                   'protocol': 'https' if self.request.is_secure() else 'http',
                                   'domain': get_current_site(request)}
                        send_email(subject, template, context, reserva.email)
                        data['url_pago'] = redirect('reservas-pago', reserva.pk).url
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Ha ocurrido un error al procesar la solicitud.'
        except Exception as e:
            data['error'] = e.args[0]
        print('ReservaUserCreateView: ', data)
        return JsonResponse(data, safe=False)


class ReservaUserListView(LoginRequiredMixin, ListView):
    """
    Vista para listar las reservas activas del usuario.
    """
    model = Reserva
    template_name = 'user/reserva/list.html'
    context_object_name = 'reservas'

    def get_queryset(self):
        return Reserva.objects.filter(email=self.request.user.email)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mis Reservas'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context


class ReservaUserDetailView(LoginRequiredMixin, DetailView):
    """
    Vista para mostrar los detalles de una reserva.
    """
    model = Reserva
    template_name = 'user/reserva/detail.html'
    context_object_name = 'reserva'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_anonymous:
            reserva = self.get_object()
            if reserva.email != request.user.email:
                messages.error(request, 'No tiene permiso para ver esta página.')
                return redirect('index')
            try:
                reserva.clean()
            except ValidationError as e:
                messages.error(request, e.args[0])
                return redirect('reservas-listado')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle de Reserva'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        try:
            context['pago_reserva'] = self.get_object().pagoreserva
        except PagoReserva.DoesNotExist:
            pass
        return context


class ReservaUserDeleteView(LoginRequiredMixin, DeleteView):
    """
    Vista para eliminar una reserva.
    """
    model = Reserva
    template_name = 'user/reserva/delete.html'

    def dispatch(self, request, *args, **kwargs):
        reserva = self.get_object()
        if reserva.is_finished():
            messages.error(request, 'La reserva ya ha sido finalizada.')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        reserva = self.get_object()
        if reserva.email != request.user.email:
            messages.error(request, 'No tiene permiso para ver esta página.')
            return redirect('index')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Baja de Reserva'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            with transaction.atomic():
                reserva = self.get_object()
                reserva.delete()
                messages.success(request, 'Reserva dada de baja exitosamente.')
        except Exception as e:
            data['error'] = e.args[0]
        print('ReservaUserDeleteView: ', data)
        return redirect('index')


class ReservaUserPaymentView(TemplateView):
    """
    Vista para realizar el pago de una reserva.
    """
    template_name = 'user/reserva/payment.html'

    def dispatch(self, request, *args, **kwargs):
        try:
            reserva = Reserva.objects.get(pk=self.kwargs['pk'])
            try:
                reserva.clean()
            except ValidationError as e:
                messages.error(request, e.args[0])
                return redirect('reservas-listado')
            if reserva.pagado:
                messages.error(request, 'La reserva ya ha sido pagada.')
                if request.user.is_authenticated and request.user.is_admin():
                    return redirect('admin-reservas-detalle', reserva.pk)
                return redirect('reservas-detalle', reserva.pk)
            if reserva.forma_pago == 1:
                messages.error(request, 'La reserva tiene forma de pago presencial.')
                if request.user.is_authenticated and request.user.is_admin():
                    return redirect('admin-reservas-detalle', reserva.pk)
                return redirect('reservas-detalle', reserva.pk)
            if reserva.is_finished():
                messages.error(request, 'La reserva ya ha finalizado.')
                if request.user.is_authenticated and request.user.is_admin():
                    return redirect('admin-reservas-detalle', reserva.pk)
                return redirect('index')
        except Reserva.DoesNotExist:
            messages.error(request, 'La reserva no existe o ha expirado.')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Pago de Reserva'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        context['public_key'] = public_key
        reserva = Reserva.objects.get(pk=self.kwargs['pk'])
        context['preference_id'] = reserva.preference_id
        context['reserva'] = reserva
        return context


class ReservaCheckoutView(View):
    """
    Vista para obtener el pago de una reserva y crear el pago en la base de datos.
    """

    def get(self, request, *args, **kwargs):
        try:
            if 'status' in request.GET:
                if request.GET['status'] == 'approved':
                    with transaction.atomic():
                        reserva = Reserva.objects.get(pk=request.GET['external_reference'])
                        payment_info = sdk.payment().get(request.GET['payment_id'])
                        pago_reserva = PagoReserva.objects.create(
                            reserva=reserva,
                            payment_id=request.GET['payment_id'],
                            status=payment_info['response']['status'],
                            status_detail=payment_info['response']['status_detail'],
                            transaction_amount=payment_info['response']['transaction_amount'],
                            date_approved=payment_info['response']['date_approved'],
                        )
                        reserva.pagado = True
                        reserva.save()
                    # Enviar correo de confirmación de pago.
                    subject = 'Reserva de Cancha - Pago Aprobado'
                    template = 'email/reserva_payment_approved.html'
                    context = {
                        'reserva': reserva,
                        'pago_reserva': pago_reserva,
                        'protocol': 'https' if request.is_secure() else 'http',
                        'domain': get_current_site(request)
                    }
                    send_email(subject, template, context, reserva.email, True)
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
            print('ReservaCheckoutView: ', e.args[0])
            messages.error(request, 'Error al realizar el pago.')
            return redirect('index')


class ReservaUserReceiptView(TemplateView):
    """
    Vista para obtener el comprobante de pago de una reserva.
    """
    template_name = 'user/reserva/receipt.html'

    def get(self, request, *args, **kwargs):
        try:
            reserva = Reserva.objects.get(pk=self.kwargs['pk'])
            pago_reserva = PagoReserva.objects.get(reserva=reserva)
            if reserva.pagado:
                return render(request, 'user/reserva/receipt.html', {
                    'title': 'Comprobante de Pago',
                    'club': Club.objects.get(pk=1),
                    'reserva': reserva,
                    'pago_reserva': pago_reserva,
                    'transaction_amount_letras': 'Son: {} pesos argentinos'.format(
                        num2words(pago_reserva.transaction_amount, lang='es')),
                    'fecha_actual': datetime.now()
                })
            else:
                messages.error(request, 'El comprobante de pago no se encuentra disponible.')
                return redirect('index')
        except (Reserva.DoesNotExist, PagoReserva.DoesNotExist):
            messages.error(request, 'El comprobante de pago no se encuentra disponible.')
            return redirect('index')


def reserva_liberada_activate(request, uidb64, token):
    """
    Vista para reservar en una cancha liberada.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and reserva_create_token.check_token(user, token):
        with transaction.atomic():
            cancha = Cancha.objects.get(pk=request.GET['cancha_pk'])
            fecha = datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date()
            hora = datetime.strptime(request.GET['hora'], '%H:%M').time()
            if not cancha.is_available(fecha, hora):
                messages.error(request, 'La cancha ya no se encuentra disponible.')
                return redirect('index')
            reserva = Reserva(
                cancha=cancha,
                nombre=user.get_full_name(),
                email=user.email,
                fecha=fecha,
                hora=hora)
            hora_laboral = HoraLaboral.objects.get(hora=hora)
            reserva.con_luz = reserva.cancha.canchahoralaboral_set.get(hora_laboral=hora_laboral).con_luz
            reserva.precio = reserva.cancha.precio_luz if reserva.con_luz else reserva.cancha.precio
            reserva.forma_pago = 2
            reserva.save()
            preference_data = {
                "items": [
                    {
                        "title": reserva.__str__(),
                        "quantity": 1,
                        "currency_id": "ARS",
                        "unit_price": float(reserva.precio),
                        "description": "Reserva de cancha {}".format(reserva.cancha.club)
                    }
                ],
                "payer": {
                    "name": reserva.nombre,
                    "email": reserva.email,
                },
                "statement_descriptor": "Reserva de cancha {}".format(reserva.cancha.club),
                "excluded_payment_types": [
                    {
                        "id": "ticket"
                    }
                ],
                "installments": 1,
                "binary_mode": True,
                "expires": True,
                "expiration_date_from": reserva.created_at.isoformat(),
                "expiration_date_to": reserva.get_expiration_date(),
                "back_urls": {
                    "success": "http://127.0.0.1:8000/reservas/checkout/",
                    "failure": "http://127.0.0.1:8000/reservas/checkout/",
                },
                "auto_return": "approved",
                "external_reference": str(reserva.pk),
            }
            preference_response = sdk.preference().create(preference_data)
            preference = preference_response["response"]
            reserva.preference_id = preference["id"]
            reserva.save()
            return redirect('reservas-pago', pk=reserva.pk)
    else:
        messages.error(request, 'El link de creación de reserva no es válido.')
        return redirect('login')


def reserva_user_ajax(request):
    data = {}
    # Obtener si el GET o POST
    try:
        if request.method == 'GET':
            action = request.GET['action']
            with transaction.atomic():
                if action == 'get_canchas_disponibles':
                    deporte_id = request.GET['deporte_id']
                    hora = request.GET['hora']
                    fecha = request.GET['fecha']
                    fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
                    hora = datetime.strptime(hora, '%H:%M:%S').time()
                    start_date = datetime.combine(fecha, hora)
                    # Fecha de inicio de la reserva debe ser con al menos 2 horas de anticipación
                    horas_anticipacion = Parameters.objects.get(club_id=1).horas_anticipacion
                    if start_date < datetime.now() + timedelta(hours=horas_anticipacion):
                        data['error'] = 'Es necesario realizar la reserva con al menos {} horas de anticipación antes' \
                                        ' del inicio.'.format(horas_anticipacion)
                        return JsonResponse(data, safe=False)
                    # Excluir las canchas que tengan reservas en esa hora y fecha y no estén eliminadas
                    canchas_disp = Cancha.objects.filter(deporte_id=deporte_id, hora_laboral__hora=hora)
                    for reserva in Reserva.global_objects.filter(cancha__deporte_id=deporte_id,
                                                                 hora=hora,
                                                                 fecha=fecha,
                                                                 is_deleted=False):
                        try:
                            reserva.clean()
                            canchas_disp = canchas_disp.exclude(id=reserva.cancha.id)
                        except ValidationError:
                            pass
                    if canchas_disp:
                        data['canchas'] = list(canchas_disp.values_list('id'))
                    else:
                        data['error'] = 'No hay canchas disponibles para la fecha y hora seleccionada.'
                elif action == 'search_horas_disponibles':
                    deporte_id = request.GET['deporte_id']
                    fecha = request.GET['fecha']
                    fecha = datetime.strptime(fecha, '%Y-%m-%d')
                    horas_anticipacion = Parameters.objects.get(club_id=1).horas_anticipacion
                    horas_disponibles = []
                    for i in range(24):
                        hora = datetime.combine(fecha, time(hour=i))
                        if hora < datetime.now() + timedelta(hours=horas_anticipacion):
                            continue
                        if hora.date() > fecha.date():
                            break
                        canchas_disp = Cancha.objects.filter(deporte_id=deporte_id,
                                                             hora_laboral__hora=hora.time()).exclude(
                            reserva__hora=hora,
                            reserva__fecha=fecha,
                            reserva__is_deleted=False)
                        if canchas_disp:
                            horas_disponibles.append(hora.strftime('%H:%M:%S'))
                    if horas_disponibles:
                        data['horas_disponibles'] = horas_disponibles
                    else:
                        data['error'] = 'No hay canchas disponibles para la fecha seleccionada.'
    except Exception as e:
        data['error'] = e.args[0]
    print('socio_user_ajax: ', data)
    return JsonResponse(data, safe=False)
