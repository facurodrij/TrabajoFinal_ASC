import mercadopago
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView, FormView
from static.credentials import MercadoPagoCredentials  # Aquí debería insertar sus credenciales de MercadoPago

from core.models import Cancha, Reserva, PagoReserva, Club

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)


# Vista para obtener canchas disponibles en una fecha y hora.
class CanchasDisponiblesView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista para obtener canchas disponibles en una fecha y hora.
    TODO: Implementar esta vista.
    """
    model = Cancha
    template_name = 'user/reserva/canchas_disponibles.html'
    context_object_name = 'canchas'
    permission_required = 'core.view_reserva'

    def get_queryset(self):
        fecha = self.request.GET.get('fecha')
        hora = self.request.GET.get('hora')
        return Cancha.objects.filter(canchahoralaboral__hora_laboral__hora=hora,
                                     canchahoralaboral__reserva__fecha=fecha,
                                     canchahoralaboral__reserva__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Canchas disponibles'
        return context


class ReservaUserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar las reservas activas del usuario.
    """
    model = Reserva
    template_name = 'user/reserva/list.html'
    context_object_name = 'reservas'
    permission_required = 'core.view_reserva'

    def get_queryset(self):
        return Reserva.objects.filter(user=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Reservas'
        return context


class ReservaPaymentView(TemplateView):
    """
    Vista para realizar el pago de una reserva.
    """
    template_name = 'user/reserva/payment.html'

    def dispatch(self, request, *args, **kwargs):
        # Verificar que la reserva no haya sido pagada.
        try:
            reserva = Reserva.objects.get(pk=self.kwargs['pk'])
            # TODO: reserva.clean()
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
