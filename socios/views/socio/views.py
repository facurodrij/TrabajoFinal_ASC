from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import FormView
from django.views.generic.list import ListView
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.db import transaction

from core.models import Club
from socios.forms import SocioForm
from socios.models import Socio, CuotaSocial
from socios.mixins import SocioRequiredMixin

from socios.payments import sdk


class SocioFormView(LoginRequiredMixin, SocioRequiredMixin, FormView):
    """
    Vista para obtener los datos del socio logueado
    """
    model = Socio
    form_class = SocioForm
    template_name = 'socio/info.html'

    # Obtener la categoria del socio
    def get_initial(self):
        socio = self.request.user.persona.get_socio()
        return {
            'categoria': socio.categoria,
        }

    def get_context_data(self, **kwargs):
        context = super(SocioFormView, self).get_context_data(**kwargs)
        context['title'] = 'Información del socio'
        context['club'] = Club.objects.get(pk=1)
        return context


class CuotaSocialListView(LoginRequiredMixin, SocioRequiredMixin, ListView):
    """
    Vista para obtener el listado de cuotas sociales del socio logueado
    """
    model = CuotaSocial
    template_name = 'socio/cuota_list.html'
    context_object_name = 'cuotas_sociales'

    def get_context_data(self, **kwargs):
        context = super(CuotaSocialListView, self).get_context_data(**kwargs)
        context['title'] = 'Mis Cuotas'
        return context

    def get_queryset(self):
        return CuotaSocial.objects.filter(detallecuotasocial__socio=self.request.user.persona.socio)

    def post(self, request, *args, **kwargs):
        user = request.user
        socio = self.request.user.persona.get_socio()
        cuota = CuotaSocial.objects.get(pk=request.POST['cuota_id'])
        preference_data = {
            "items": [
                {
                    "title": "Cuota Social",
                    "quantity": 1,
                    "currency_id": "ARS",
                    "unit_price": float(cuota.total),
                }
            ],
            "payer": {
                "name": user.persona.nombre,
                "surname": user.persona.apellido,
                "email": user.email,
                "identification": {
                    "type": "DNI",
                    "number": user.persona.dni,
                },
            },
            "back_urls": {
                "success": "http://127.0.0.1:8000/socio/mis_cuotas/",
                "failure": "http://127.0.0.1:8000/socio/mis_cuotas/",
                "pending": "http://127.0.0.1:8000/socio/mis_cuotas/",
            },
            "auto_return": "approved",
            "external_reference": str(cuota.id),
            "payment_methods": {
                "excluded_payment_types": [
                    {
                        "id": "ticket"
                    }
                ],
                "installments": 1,
            },
        }
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        return JsonResponse(preference, safe=False)

    def get(self, request, *args, **kwargs):
        if 'collection_status' in request.GET:
            if request.GET['collection_status'] == 'approved':
                cuota = CuotaSocial.objects.get(pk=request.GET['external_reference'])
                with transaction.atomic():
                    cuota.fecha_pago = datetime.now()
                    cuota.save()
                messages.success(request, 'Pago realizado con éxito')
            else:
                messages.error(request, 'No se pudo realizar el pago')
            return redirect(reverse_lazy('socio-cuotas'))
        return super(CuotaSocialListView, self).get(request, *args, **kwargs)
