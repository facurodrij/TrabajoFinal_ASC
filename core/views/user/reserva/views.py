import mercadopago
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView, CreateView, DeleteView, DetailView

from core.forms import ReservaUserForm
from core.models import Reserva, PagoReserva, Club
from static.credentials import MercadoPagoCredentials  # Aquí debería insertar sus credenciales de MercadoPago

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)


# Vista para que el usuario pueda reservar una cancha
class ReservaUserCreateView(LoginRequiredMixin, CreateView):
    """
    Vista para obtener canchas disponibles en una fecha y hora determinada.
    """
    model = Reserva
    template_name = 'user/reserva/form.html'
    form_class = ReservaUserForm

    # TODO: Establecer un limite de reservas por usuario.

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        try:
            form.fields['deporte'].initial = self.request.GET['deporte']
            form.fields['fecha'].initial = self.request.GET['fecha']
            form.fields['hora'].initial = self.request.GET['hora']
        except KeyError:
            pass
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
            form = self.form_class(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    reserva = form.save()
                    # TODO: Enviar correo con el link de pago.
                messages.success(request, 'Reserva creada exitosamente.')
                return redirect('reservas-pago', pk=reserva.pk)
            else:
                data['error'] = form.errors
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
        reserva = self.get_object()
        if reserva.email != request.user.email:
            messages.error(request, 'No tiene permiso para ver esta página.')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle de Reserva'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context


class ReservaUserDeleteView(DeleteView):
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
                # TODO: Ejecutar proceso autamatizado de aviso de baja de reserva.
        except Exception as e:
            data['error'] = e.args[0]
        print('ReservaUserDeleteView: ', data)
        return redirect('index')


class ReservaPaymentView(TemplateView):
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
                return redirect('index')
            if reserva.is_paid():
                messages.error(request, 'La reserva ya ha sido pagada.')
                return redirect('index')
            if reserva.is_finished():
                messages.error(request, 'La reserva ya ha finalizado.')
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


class ReservaCheckoutView(TemplateView):
    """
    Vista para realizar el pago de una reserva con MercadoPago.
    """
    template_name = 'user/reserva/checkout.html'

    def get(self, request, *args, **kwargs):
        if 'status' in request.GET:
            if request.GET['status'] == 'approved':
                payment_id = request.GET['payment_id']
                preference_id = request.GET['preference_id']
                payment_info = sdk.payment().get(payment_id)
                reserva_id = payment_info['response']['external_reference']
                try:
                    with transaction.atomic():
                        reserva = Reserva.objects.get(id=reserva_id)
                        pago_reserva = PagoReserva(
                            payment_id=payment_id,
                            reserva=reserva,
                            preference_id=preference_id,
                            date_created=payment_info['response']['date_created'],
                            date_approved=payment_info['response']['date_approved'],
                            date_last_updated=payment_info['response']['date_last_updated'],
                            payment_method_id=payment_info['response']['payment_method_id'],
                            payment_type_id=payment_info['response']['payment_type_id'],
                            status=payment_info['response']['status'],
                            status_detail=payment_info['response']['status_detail'],
                            transaction_amount=payment_info['response']['transaction_amount'],
                        )
                        pago_reserva.save()
                        messages.success(request, 'El pago se ha realizado con éxito.')
                        # TODO: Enviar correo de confirmación de pago.
                        return redirect('index')
                except Exception as e:
                    messages.error(request, 'El pago no se ha realizado con éxito.')
                    # TODO: Cancelar o reembolsar el pago.
                    return redirect('index')
            else:
                messages.error(request, 'Su pago ha sido rechazado.')
                return redirect('index')
        else:
            return super().get(request, *args, **kwargs)
