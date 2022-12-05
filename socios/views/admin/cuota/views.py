from datetime import datetime

import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import ListView
from weasyprint import HTML, CSS

from accounts.decorators import admin_required
from core.models import Club
from parameters.models import ClubParameters, MedioPago
from socios.models import CuotaSocial, PagoCuotaSocial


class CuotaSocialAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para listar las cuotas sociales, solo para administradores """
    model = CuotaSocial
    template_name = 'admin/cuota/list.html'
    permission_required = 'socios.view_cuotasocial'
    context_object_name = 'cuotas_sociales'

    def get_queryset(self):
        return CuotaSocial.global_objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cuotas Sociales'
        context['medios_pagos'] = MedioPago.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'get_total_cuota_social':
                # Si la acción es get_total_cuota_social, se calcula el total de la cuota social
                cuota_social = CuotaSocial.objects.get(pk=request.POST['id'])
                # Calcular intereses
                if cuota_social.fecha_vencimiento < datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')):
                    aumento_por_cuota_vencida = ClubParameters.objects.get(pk=1).aumento_por_cuota_vencida
                    # Calcular los meses de atraso
                    meses_atraso = (datetime.now(pytz.timezone(
                        'America/Argentina/Buenos_Aires')).year - cuota_social.fecha_vencimiento.year) * 12 + (
                                           datetime.now(pytz.timezone(
                                               'America/Argentina/Buenos_Aires')).month - cuota_social.fecha_vencimiento.month)
                    interes = cuota_social.total * (aumento_por_cuota_vencida / 100) * meses_atraso
                    total_w_interes = cuota_social.total + interes
                    data['meses_atraso'] = meses_atraso
                    data['interes_por_mes'] = aumento_por_cuota_vencida
                    data['interes'] = round(interes, 2)
                    data['total_w_interes'] = round(total_w_interes, 2)
                else:
                    data['total'] = cuota_social.total
            elif action == 'mark_as_paid':
                # Si la acción es mark_as_paid, se marca una cuota social como pagada
                cuota_social = CuotaSocial.objects.get(pk=request.POST['id'])
                with transaction.atomic():
                    medio_pago = MedioPago.objects.get(pk=request.POST['medio_pago'])
                    PagoCuotaSocial.objects.create(
                        cuota_social=cuota_social,
                        medio_pago=medio_pago,
                        fecha_pago=datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')),
                        total_pagado=request.POST['total_pagado'])
                    cuota_social.observaciones = request.POST['observaciones']
                    cuota_social.save()
                    data['id'] = request.POST['id']
                    data['history_id'] = cuota_social.history.first().pk
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = str(e)
        print(data)
        return JsonResponse(data, safe=False)


@login_required
@admin_required
def cuota_delete(request, pk):
    """
    Eliminar una cuota social
    """
    cuota = get_object_or_404(CuotaSocial, pk=pk)
    # Obtener el motivo de la eliminación en la url ?motivo=...
    motivo = request.GET.get('motivo', None)
    with transaction.atomic():
        cuota._change_reason = motivo
        cuota.delete(cascade=True)
        messages.success(request, 'Cuota social eliminada correctamente')
    return redirect(request.META.get('HTTP_REFERER'))


@login_required
@admin_required
def cuota_history_pdf(request, cuota_pk, history_pk):
    cuota = CuotaSocial.global_objects.get(pk=cuota_pk)
    club = Club.objects.get(pk=1)
    history = cuota.history.get(pk=history_pk)
    html_string = render_to_string('admin/cuota/history_pdf.html', {'history': history,
                                                                    'cuota': cuota,
                                                                    'club': club})
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    html.write_pdf(target='/tmp/cuota_historial.pdf',
                   stylesheets=[CSS('{}/libs/bootstrap-4.6.2/bootstrap.min.css'.format(settings.STATICFILES_DIRS[0]))])
    fs = FileSystemStorage('/tmp')
    with fs.open('cuota_historial.pdf') as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="cuota_historial.pdf"'
        return response
