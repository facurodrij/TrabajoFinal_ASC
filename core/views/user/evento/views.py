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
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import ListView, TemplateView, CreateView, DeleteView, DetailView, FormView

from accounts.views import User
from core.forms import ReservaUserForm
from core.models import Reserva, PagoReserva, Club, Cancha, HoraLaboral, Evento
from core.tokens import reserva_create_token
from static.credentials import MercadoPagoCredentials  # Aquí debería insertar sus credenciales de MercadoPago

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)

UserModel = get_user_model()


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
        return context
