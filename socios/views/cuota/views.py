from datetime import datetime

import mercadopago
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic.list import ListView
from weasyprint import HTML, CSS

from accounts.models import Persona
from core.models import Club
from socios.mixins import SocioRequiredMixin
from socios.models import CuotaSocial, DetalleCuotaSocial
from static.credentials import MercadoPagoCredentials  # Aquí debería insertar sus credenciales de MercadoPago

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)


class CuotaSocialListView(LoginRequiredMixin, SocioRequiredMixin, ListView):
    """
    Vista para obtener el listado de cuotas sociales del socio logueado
    """
    model = CuotaSocial
    template_name = 'cuota/list.html'
    context_object_name = 'cuotas_sociales'

    def get_context_data(self, **kwargs):
        context = super(CuotaSocialListView, self).get_context_data(**kwargs)
        context['title'] = 'Mis Cuotas'
        context['public_key'] = public_key
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
                    "title": "Cuota Social #{}".format(cuota.id),
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


class CuotaSocialWOAListView(ListView):
    """
    Vista para obtener el listado de cuotas sociales sin autenticación
    """
    model = CuotaSocial
    template_name = 'cuota/list_woa.html'
    context_object_name = 'cuotas_sociales'

    def get_context_data(self, **kwargs):
        context = super(CuotaSocialWOAListView, self).get_context_data(**kwargs)
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        context['public_key'] = public_key
        return context

    def get_queryset(self):
        # Obtener el dni de la url
        dni = self.kwargs['dni']
        persona = Persona.objects.get(dni=dni)
        return CuotaSocial.objects.filter(detallecuotasocial__socio=persona.socio)

    def post(self, request, *args, **kwargs):
        cuota = CuotaSocial.objects.get(pk=request.POST['cuota_id'])
        dni = str(self.kwargs['dni'])
        preference_data = {
            "items": [
                {
                    "title": "Cuota Social #{}".format(cuota.id),
                    "quantity": 1,
                    "currency_id": "ARS",
                    "unit_price": float(cuota.total),
                }
            ],
            "back_urls": {
                "success": "http://127.0.0.1:8000/cuotas/dni=" + dni + "/",
                "failure": "http://127.0.0.1:8000",
                "pending": "http://127.0.0.1:8000",
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
            return redirect(reverse_lazy('cuotas-sin-autenticacion', kwargs={'dni': self.kwargs['dni']}))
        return super(CuotaSocialWOAListView, self).get(request, *args, **kwargs)


# Generar PDF con weasyprint del detalle de la cuota social
def cuota_social_pdf(request, pk):
    cuota = CuotaSocial.global_objects.get(pk=pk)
    club = Club.objects.get(pk=1)
    detalle_cuota = DetalleCuotaSocial.global_objects.filter(cuota_social=cuota)
    html_string = render_to_string('cuota/pdf.html', {'cuota': cuota, 'club': club, 'detalle_cuota': detalle_cuota})
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    html.write_pdf(target='/tmp/cuota.pdf',
                   stylesheets=[CSS('https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css')])
    fs = FileSystemStorage('/tmp')
    with fs.open('cuota.pdf') as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="cuota.pdf"'
        return response