from datetime import datetime, date, timedelta

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
from parameters.models import MedioPago
from socios.models import CuotaSocial, PagoCuotaSocial, Socio, ItemCuotaSocial, Parameters


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
                if cuota_social.is_atrasada():
                    aumento_por_cuota_vencida = Parameters.objects.get(pk=1).aumento_por_cuota_vencida
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
            elif action == 'generar_deudas':
                # Si la acción es generar_deudas, se generan las deudas de las cuotas sociales
                socios = Socio.objects.all()
                periodo_mes = request.POST['periodo_mes']
                periodo_anio = request.POST['periodo_anio']
                parameters_dia_vencimiento = Parameters.objects.get(pk=1).dia_vencimiento_cuota
                periodo_date = date(int(periodo_anio), int(periodo_mes), 1)
                cuotas = 0
                for socio in socios.filter(date_created__lte=periodo_date):
                    categoria = socio.get_categoria()
                    if socio.persona.es_titular() and socio.itemcuotasocial_set.filter(
                            cuota_social__periodo_mes=periodo_mes,
                            cuota_social__periodo_anio=periodo_anio).count() == 0:
                        with transaction.atomic():
                            cuota_social = CuotaSocial.objects.create(
                                persona=socio.persona,
                                fecha_emision=datetime.now(),
                                fecha_vencimiento=datetime.now() + timedelta(days=parameters_dia_vencimiento, hours=00,
                                                                             minutes=00, seconds=00),
                                periodo_mes=periodo_mes,
                                periodo_anio=periodo_anio,
                            )
                            cuota_social.save()
                            # Agregar el detalle de la cuota social
                            detalle = ItemCuotaSocial()
                            detalle.cuota_social = cuota_social
                            detalle.socio = socio
                            detalle.nombre_completo = socio.persona.get_full_name()
                            detalle.categoria = categoria.__str__()
                            detalle.save()
                            for miembro in socio.get_miembros():
                                detalle_miembro = ItemCuotaSocial()
                                detalle_miembro.cuota_social = cuota_social
                                detalle_miembro.socio = miembro
                                detalle_miembro.nombre_completo = miembro.persona.get_full_name()
                                detalle_miembro.categoria = miembro.get_categoria().__str__()
                                detalle_miembro.save()
                            # Generar el total, sumando los totales parciales de los detalles relacionados.
                            total = cuota_social.cargo_extra
                            for detalle in cuota_social.itemcuotasocial_set.all():
                                total += detalle.total_parcial
                            cuota_social.total = total
                            cuota_social.save()
                            cuotas += 1
                if cuotas > 0:
                    messages.success(request, 'Cuota/s social/es agregada/s correctamente')
                else:
                    messages.error(request,
                                   'No se agregaron cuotas sociales, ningún socio ha sido dado de alta antes '
                                   'del periodo seleccionado')
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
