from datetime import datetime

import mercadopago
import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic.list import ListView
from weasyprint import HTML, CSS

from core.models import Club
from parameters.models import ClubParameters, MedioPago
from socios.mixins import SocioRequiredMixin
from socios.models import CuotaSocial, DetalleCuotaSocial, PagoCuotaSocial
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
        context['cuotas_sociales_pagadas'] = CuotaSocial.objects.filter(
            detallecuotasocial__socio=self.request.user.persona.socio).exclude(
            pagocuotasocial__isnull=True).order_by('pagocuotasocial__fecha_pago')
        return context

    def get_queryset(self):
        # Filtrar las cuotas sociales por fecha de vencimiento de tal forma que las pagadas queden al final
        return CuotaSocial.objects.filter(
            detallecuotasocial__socio=self.request.user.persona.socio).exclude(
            pagocuotasocial__isnull=False).order_by('fecha_vencimiento')

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'get_total_cuota_social':
                # Si la acción es get_total_cuota_social, se calcula el total de la cuota social
                cuota_social = CuotaSocial.objects.get(pk=request.POST['id'], persona=request.user.persona)
                all_cuota_social = CuotaSocial.objects.filter(persona=request.user.persona).exclude(
                    pagocuotasocial__isnull=False)
                # Ordenar por fecha de vencimiento
                all_cuota_social = all_cuota_social.order_by('fecha_vencimiento')
                # Verificar que cuota_social sea la primera all_cuota_social
                if cuota_social == all_cuota_social.first():
                    # Calcular intereses
                    if cuota_social.is_atrasada():
                        aumento_por_cuota_vencida = ClubParameters.objects.get(pk=1).aumento_por_cuota_vencida
                        # Calcular los meses de atraso
                        meses_atraso = cuota_social.meses_atraso()
                        interes = cuota_social.interes()
                        total_w_interes = cuota_social.total + interes
                        data['meses_atraso'] = meses_atraso
                        data['interes_por_mes'] = aumento_por_cuota_vencida
                        data['interes'] = interes
                        data['total_w_interes'] = round(total_w_interes, 2)
                    else:
                        data['total'] = cuota_social.total
                else:
                    data['error'] = 'Debe pagar primero la cuota social con el período más antiguo'
            elif action == 'checkout':
                user = request.user
                socio = self.request.user.persona.get_socio()
                cuota = CuotaSocial.objects.get(pk=request.POST['cuota_id'])
                preference_data = {
                    "items": [
                        {
                            "title": "Cuota Social #{}".format(cuota.id),
                            "quantity": 1,
                            "currency_id": "ARS",
                            "unit_price": float(request.POST['total_a_pagar']),
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
                        "success": "http://127.0.0.1:8000/cuotas/mis_cuotas/",
                        "failure": "http://127.0.0.1:8000/cuotas/mis_cuotas/",
                        "pending": "http://127.0.0.1:8000/cuotas/mis_cuotas/",
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
                # Generar comprobante de pago
                preference_response = sdk.preference().create(preference_data)
                preference = preference_response["response"]
                # Agregar parametro extra al response
                preference["transaction_amount"] = request.POST['total_a_pagar']
                return JsonResponse(preference, safe=False)
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        print(data)
        return JsonResponse(data, safe=False)

    def get(self, request, *args, **kwargs):
        if 'collection_status' in request.GET:
            if request.GET['collection_status'] == 'approved':
                cuota_social = CuotaSocial.objects.get(pk=request.GET['external_reference'])
                # Calcular intereses
                if cuota_social.is_atrasada():
                    aumento_por_cuota_vencida = ClubParameters.objects.get(pk=1).aumento_por_cuota_vencida
                    # Calcular los meses de atraso
                    meses_atraso = cuota_social.meses_atraso()
                    interes = cuota_social.interes()
                    total_w_interes = cuota_social.total + interes
                    total_pagado = round(total_w_interes, 2)
                    cuota_social.observaciones = 'Se han aplicado los intereses correspondientes a la mora'
                    cuota_social.save()
                else:
                    total_pagado = cuota_social.total
                with transaction.atomic():
                    PagoCuotaSocial.objects.create(
                        cuota_social=cuota_social,
                        fecha_pago=datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')),
                        medio_pago=MedioPago.objects.get(pk=6),
                        total_pagado=total_pagado,
                    )
                    messages.success(request, 'Pago realizado con éxito')
                    return redirect('socio-cuotas')
            else:
                messages.error(request, 'No se pudo realizar el pago')
            return redirect(reverse_lazy('socio-cuotas'))
        return super(CuotaSocialListView, self).get(request, *args, **kwargs)


# Generar PDF con weasyprint del detalle de la cuota social
@login_required
def cuota_social_pdf(request, pk):
    cuota = CuotaSocial.global_objects.get(pk=pk)
    club = Club.objects.get(pk=1)
    detalle_cuota = DetalleCuotaSocial.global_objects.filter(cuota_social=cuota)
    html_string = render_to_string('cuota/pdf.html', {'cuota': cuota, 'club': club, 'detalle_cuota': detalle_cuota})
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    html.write_pdf(target='/tmp/cuota.pdf',
                   stylesheets=[CSS('{}/libs/bootstrap-4.6.2/bootstrap.min.css'.format(settings.STATICFILES_DIRS[0]))])
    fs = FileSystemStorage('/tmp')
    with fs.open('cuota.pdf') as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="cuota.pdf"'
        return response
