from datetime import datetime, timedelta

import mercadopago
import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.list import ListView
from num2words import num2words
from weasyprint import HTML, CSS

from core.models import Club
from socios.models import CuotaSocial, ItemCuotaSocial, PagoCuotaSocial, PagoCuotaSocialCuotas
from static.credentials import MercadoPagoCredentials  # Aquí debería insertar sus credenciales de MercadoPago

public_key = MercadoPagoCredentials.get_public_key()
access_token = MercadoPagoCredentials.get_access_token()
sdk = mercadopago.SDK(access_token)


class CuotaSocialUserListView(LoginRequiredMixin, ListView):
    """
    Vista para obtener el listado de cuotas sociales de la persona autenticada.
    """
    model = CuotaSocial
    template_name = 'user/cuota/list.html'
    context_object_name = 'cuotas_sociales'

    def get_context_data(self, **kwargs):
        context = super(CuotaSocialUserListView, self).get_context_data(**kwargs)
        context['title'] = 'Mis Cuotas Sociales Pendientes'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context

    def get_queryset(self):
        # Filtrar las cuotas sociales pendientes del socio autenticado, ordenadas por periodo
        return CuotaSocial.objects.filter(
            itemcuotasocial__socio=self.request.user.socio
        ).exclude(pagocuotasocialcuotas__isnull=False).order_by('periodo_anio', 'periodo_mes')

    # TODO: Excluir aquellas cuotas que ya fueron pagadas en periodos anteriores

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            cuotas = CuotaSocial.objects.filter(
                pk__in=request.POST.getlist('ids[]')
            ).order_by('periodo_anio', 'periodo_mes')
            # Verificar que las cuotas seleccionadas sean las primeras de la lista de cuotas sociales
            for cuota, i in zip(cuotas, range(len(cuotas))):
                if cuota != self.get_queryset()[i]:
                    data['error'] = 'Las cuotas seleccionadas deben ser seleccionadas en orden por períodos'
                    return JsonResponse(data, safe=False)
            # Guardar en session las cuotas seleccionadas
            request.session['cuotas'] = [cuota.pk for cuota in cuotas]
        except Exception as e:
            data['error'] = e.args[0]
        return JsonResponse(data, safe=False)


class CuotaSocialUserOrderView(LoginRequiredMixin, TemplateView):
    """
    Vista para obtener el listado de cuotas sociales guardadas en session.
    """
    template_name = 'user/cuota/orden.html'

    def dispatch(self, request, *args, **kwargs):
        try:
            if 'cuotas' not in request.session:
                return redirect('cuotas-listado')
            return super(CuotaSocialUserOrderView, self).dispatch(request, *args, **kwargs)
        except Exception as e:
            return redirect('cuotas-listado')

    def get_context_data(self, **kwargs):
        context = super(CuotaSocialUserOrderView, self).get_context_data(**kwargs)
        context['title'] = 'Orden de Pago'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        context['cuotas'] = CuotaSocial.objects.filter(pk__in=self.request.session['cuotas'])
        subtotal = 0
        interes = 0
        for cuota in context['cuotas']:
            subtotal += cuota.total
            interes += cuota.interes()
        context['subtotal'] = subtotal
        context['interes'] = interes
        total = subtotal + interes
        context['total'] = total
        context['total_letras'] = 'Son: {} pesos argentinos'.format(num2words(total, lang='es'))
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            # Crear el checkout de mercadopago con las cuotas seleccionadas en session
            cuotas = CuotaSocial.objects.filter(pk__in=request.session['cuotas'])
            total = 0
            for cuota in cuotas:
                if cuota.is_pagada():
                    raise ValidationError('Ya se realizó el pago de una de las cuotas seleccionadas')
                total += cuota.total_a_pagar()
            site = get_current_site(request)
            preference = {
                "items": [
                    {
                        "title": "Pago de Cuotas Sociales",
                        "quantity": 1,
                        "currency_id": "ARS",
                        "unit_price": float(total),
                    }
                ],
                "payer": {
                    "email": request.user.email,
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
                "expiration_date_from": datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).isoformat(),
                "expiration_date_to": (datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')) + timedelta(
                    minutes=10)).isoformat(),
                "back_urls": {
                    "success": "{}://{}{}".format('https' if self.request.is_secure() else 'http', site.domain,
                                                  reverse('cuotas-checkout')),
                    "failure": "{}://{}{}".format('https' if self.request.is_secure() else 'http', site.domain,
                                                  reverse('cuotas-checkout')),
                },
                "auto_return": "approved",
                "external_reference": request.session['cuotas'],
            }
            preference_result = sdk.preference().create(preference)
            preference_id = preference_result['response']['id']
        except (ValidationError, Exception) as e:
            data['error'] = e.args[0]
            return JsonResponse(data, safe=False)
        return JsonResponse({
            'preference_id': preference_id,
            'public_key': public_key
        }, safe=False)


class CuotaSocialUserCheckoutView(View):
    """
    Vista para obtener el pago de una o varias cuotas sociales.
    """

    def get(self, request, *args, **kwargs):
        try:
            if 'status' in request.GET:
                if request.GET['status'] == 'approved':
                    with transaction.atomic():
                        # Obtener el id de la cuota social con external_reference
                        external_references = request.GET['external_reference']
                        ids = [int(id.strip()) for id in external_references.strip('[]').split(',')]
                        cuotas = CuotaSocial.objects.filter(pk__in=ids)
                        payment_info = sdk.payment().get(request.GET['payment_id'])
                        # Con todas las cuotas, crear solo un pago de cuota social
                        pago = PagoCuotaSocial.objects.create(
                            medio_pago="MercadoPago",
                            fecha_pago=datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')),
                            subtotal=0,
                            interes_aplicado=0,
                            total_pagado=payment_info['response']['transaction_amount'],
                            payment_id=request.GET['payment_id'],
                            status=payment_info['response']['status'],
                            status_detail=payment_info['response']['status_detail'],
                            date_approved=payment_info['response']['date_approved'],
                        )
                        subtotal = 0
                        interes = 0
                        total = 0
                        for cuota in cuotas:
                            subtotal += cuota.total
                            interes += cuota.interes()
                            total += cuota.total_a_pagar()
                            # pago.cuotas.add(cuota), no puedo hacer esto porque hay una tabla intermedia con mas campos
                            PagoCuotaSocialCuotas.objects.create(
                                pago_cuota_social=pago,
                                cuota_social=cuota,
                                interes_aplicado=cuota.interes(),
                                subtotal=cuota.total,
                                total_pagado=cuota.total_a_pagar()
                            )
                        pago.subtotal = subtotal
                        pago.interes_aplicado = interes
                        pago.total_pagado = total
                        pago.save()
                    messages.success(request, 'Pago realizado con éxito.')
                    return redirect('cuotas-comprobante', pk=pago.pk)
                else:
                    messages.error(request, 'Error al realizar el pago.')
                    return redirect('index')
            else:
                messages.error(request, 'Error al realizar el pago.')
                return redirect('index')
        except Exception as e:
            print('CuotaSocialUserCheckoutView: ', e.args[0])
            messages.error(request, 'Error al realizar el pago.')
            return redirect('index')


class PagoCuotaSocialUserReceiptView(TemplateView):
    """
    Vista para obtener el comprobante de pago de una cuota social.
    """
    template_name = 'user/cuota/receipt.html'

    def dispatch(self, request, *args, **kwargs):
        try:
            PagoCuotaSocial.objects.get(pk=kwargs['pk'])
            return super(PagoCuotaSocialUserReceiptView, self).dispatch(request, *args, **kwargs)
        except (PagoCuotaSocial.DoesNotExist, KeyError):
            messages.error(request, 'El comprobante de pago no se encuentra disponible.')
            return redirect('cuotas-listado')

    def get_context_data(self, **kwargs):
        context = super(PagoCuotaSocialUserReceiptView, self).get_context_data(**kwargs)
        context['title'] = 'Comprobante de Pago de Cuota Social'
        context['club'] = Club.objects.get(pk=1)
        context['pago_cuota_social'] = PagoCuotaSocial.objects.get(pk=kwargs['pk'])
        context['total_pagado_letras'] = 'Son: {} pesos argentinos'.format(
            num2words(context['pago_cuota_social'].total_pagado, lang='es'))
        context['fecha_actual'] = datetime.now()
        return context


# Generar PDF con weasyprint del detalle de la cuota social
@login_required
def cuota_social_pdf(request, pk):
    cuota = CuotaSocial.global_objects.get(pk=pk)
    club = Club.objects.get(pk=1)
    detalle_cuota = ItemCuotaSocial.objects.filter(cuota_social=cuota)
    html_string = render_to_string('user/cuota/pdf.html',
                                   {'cuota': cuota, 'club': club, 'detalle_cuota': detalle_cuota})
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    html.write_pdf(target='/tmp/cuota.pdf',
                   stylesheets=[CSS('{}/libs/bootstrap-4.6.2/bootstrap.min.css'.format(settings.STATICFILES_DIRS[0]))])
    fs = FileSystemStorage('/tmp')
    with fs.open('cuota.pdf') as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="cuota.pdf"'
        return response
