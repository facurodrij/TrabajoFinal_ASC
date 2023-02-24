from datetime import datetime

import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.generic import ListView, DetailView, TemplateView
from num2words import num2words
from weasyprint import HTML, CSS

from accounts.decorators import admin_required
from core.models import Club, Persona
from parameters.models import MedioPago
from socios.models import CuotaSocial, ItemCuotaSocial, Parameters, PagoCuotaSocial, PagoCuotaSocialCuotas


class CuotaSocialAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para listar las cuotas sociales, solo para administradores """
    model = CuotaSocial
    template_name = 'admin/cuota/list.html'
    permission_required = 'socios.view_cuotasocial'
    context_object_name = 'cuotas_sociales'

    def get_queryset(self):
        # Ordenar las cuotas sociales por periodo, de mas antiguo a mas reciente
        return CuotaSocial.global_objects.all().order_by('periodo_anio', 'periodo_mes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cuotas Sociales'
        context['medios_pagos'] = MedioPago.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if 'action' in request.POST:
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
                    return JsonResponse(data, safe=False)
                elif action == 'mark_as_paid':
                    # Si la acción es mark_as_paid, se marca una cuota social como pagada
                    cuota_social = CuotaSocial.objects.get(pk=request.POST['id'])
                    with transaction.atomic():
                        medio_pago = MedioPago.objects.get(pk=request.POST['medio_pago'])
                        pago = PagoCuotaSocial.objects.create(
                            medio_pago=medio_pago.nombre,
                            fecha_pago=datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')),
                            subtotal=cuota_social.total,
                            interes_aplicado=cuota_social.interes(),
                            total_pagado=request.POST['total_pagado'],
                            payment_id=cuota_social.pk,
                            status='approved',
                            status_detail='approved',
                            date_approved=datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')),
                        )
                        cuota_social.observaciones = request.POST['observaciones']
                        cuota_social.save()
                        PagoCuotaSocialCuotas.objects.create(
                            pago_cuota_social=pago,
                            cuota_social=cuota_social,
                            interes_aplicado=cuota_social.interes(),
                            subtotal=cuota_social.total,
                            total_pagado=cuota_social.total_a_pagar()
                        )
                        data['id'] = request.POST['id']
                        return JsonResponse(data, safe=False)
            else:
                periodo = request.POST['periodo']
                request.session['periodo_mes'] = periodo.split('/')[0]
                request.session['periodo_anio'] = periodo.split('/')[1]
        except Exception as e:
            data['error'] = e.args[0]
            messages.error(request, e.args[0])
            return redirect('admin-cuota-listado')
        return redirect('admin-cuota-generar')


class CuotaSocialAdminDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = CuotaSocial
    template_name = 'admin/cuota/detail.html'
    permission_required = 'cuota_social.view_cuotasocial'
    context_object_name = 'cuota_social'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle de Cuota Social'
        return context


class CuotaSocialAdminGenerateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista para generar las cuotas sociales en un periodo (mes/año) determinado. Se generan las cuotas sociales a los
    socios seleccionados.
    """
    template_name = 'admin/cuota/generate.html'
    permission_required = 'cuota_social.add_cuotasocial'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Generar Cuotas Sociales'
        # Obtener el mes y año de la session
        periodo_mes = self.request.session.get('periodo_mes', None)
        periodo_anio = self.request.session.get('periodo_anio', None)
        if periodo_mes is None or periodo_anio is None:
            messages.error(self.request, 'Debe seleccionar un periodo para generar las cuotas sociales')
            return redirect('admin-cuota-listado')
        context['periodo'] = periodo_mes + '/' + periodo_anio
        # Filtrar por las personas que sean titulares, que sean socios o que tengan almenos un miembro como socio
        # creado antes del periodo seleccionado y que no tengan una cuota social generada para el periodo
        # seleccionado.
        personas_json = []
        persona_validas = Persona.objects.filter(
            persona_titular__isnull=True
        ).exclude(
            cuotasocial__periodo_mes=periodo_mes, cuotasocial__periodo_anio=periodo_anio
        )
        for persona in persona_validas:
            if not persona.get_socio() and persona.persona_set.all().count() == 0:
                persona_validas = persona_validas.exclude(pk=persona.pk)
                continue
            # Quitamos las personas que no son socios y no tienen ninguna persona a cargo.

            if not persona.get_socio() and persona.persona_set.all().count() > 0:
                socio = 0
                for miembro in persona.persona_set.all():
                    if miembro.get_socio() and miembro.get_socio().date_created <= \
                            datetime(int(periodo_anio), int(periodo_mes), 1, tzinfo=pytz.timezone(settings.TIME_ZONE)):
                        socio += 1
                if socio == 0:
                    persona_validas = persona_validas.exclude(pk=persona.pk)
                    continue
            # Quitamos las personas que no son socios y tienen personas a cargo, pero ninguna de ellas
            # son socios activos o son socios creados antes del periodo seleccionado.

            if persona.get_socio() and persona.socio.grupo_familiar().__len__() == 1:
                if persona.socio.date_created > datetime(int(periodo_anio), int(periodo_mes), 1,
                                                         tzinfo=pytz.timezone(settings.TIME_ZONE)):
                    persona_validas = persona_validas.exclude(pk=persona.pk)
                    continue
            # Quitamos las personas que son socios y no tienen personas a cargo, pero el socio fue creado
            # después del periodo seleccionado.

            if persona.get_socio() and persona.socio.grupo_familiar().__len__() > 1:
                socio = 0
                for miembro in persona.socio.grupo_familiar():
                    if not miembro.is_deleted and miembro.date_created <= \
                            datetime(int(periodo_anio), int(periodo_mes), 1, tzinfo=pytz.timezone(settings.TIME_ZONE)):
                        socio += 1
                if socio == 0:
                    persona_validas = persona_validas.exclude(pk=persona.pk)
                    continue
            # Quitamos las personas que son socios y tienen personas a cargo, pero ninguna de ellas
            # son socios activos o son socios creados antes del periodo seleccionado.

            # Crear la cuota social en formato json para ser utilizada en el template
            persona.cuota_social = {
                'persona': persona.pk,
                'fecha_emision': datetime.now().strftime('%d/%m/%Y'),
                'periodo_mes': datetime(int(periodo_anio), int(periodo_mes), 1).strftime('%B').capitalize(),
                'periodo_anio': periodo_anio,
                'fecha_vencimiento': datetime(int(periodo_anio), int(periodo_mes), 28).strftime('%d/%m/%Y'),
                'items': []
            }
            # Agregar los items de la cuota social
            if persona.get_socio():
                for miembro in persona.socio.grupo_familiar():
                    persona.cuota_social['items'].append({
                        'socio': miembro.pk,
                        'nombre_completo': miembro.persona.get_full_name(),
                        'categoria': miembro.get_categoria().__str__(),
                        'cuota': miembro.get_categoria().cuota.__str__(),
                        'cargo_extra': 0,
                        'total_parcial': miembro.get_categoria().cuota.__str__()
                    })
            else:
                for miembro in persona.persona_set.all():
                    if miembro.get_socio() and miembro.get_socio().date_created <= \
                            datetime(int(periodo_anio), int(periodo_mes), 1, tzinfo=pytz.timezone(settings.TIME_ZONE)):
                        persona.cuota_social['items'].append({
                            'socio': miembro.pk,
                            'nombre_completo': miembro.get_full_name(),
                            'categoria': miembro.socio.get_categoria().__str__(),
                            'cuota': miembro.socio.get_categoria().cuota.__str__(),
                            'cargo_extra': 0,
                            'total_parcial': miembro.socio.get_categoria().cuota.__str__()
                        })

            # Agregar el total de la cuota social
            total = 0
            for item in persona.cuota_social['items']:
                total += float(item['cuota'])
            persona.cuota_social['total'] = total.__str__()
            persona.cuota_social['total_letras'] = 'Son: {}'.format(num2words(total, lang='es'))
            personas_json.append(persona)
        context['personas'] = personas_json
        return context

    def post(self, request, *args, **kwargs):
        """
        Generar las cuotas sociales
        """
        data = {}
        try:
            # Obtener las ids de las personas seleccionadas
            personas = Persona.objects.filter(pk__in=request.POST.getlist('ids[]'))
            # Obtener el periodo de las cuotas sociales
            periodo = request.POST.get('periodo')
            periodo_mes, periodo_anio = periodo.split('/')
            # Crear las cuotas sociales
            for persona in personas:
                with transaction.atomic():
                    cuota = CuotaSocial.objects.create(
                        persona=persona,
                        fecha_emision=timezone.now(),
                        fecha_vencimiento=datetime(int(periodo_anio), int(periodo_mes), 28, 0, 0, 0, 0),
                        # TODO: Parametrizar el vencimiento de las cuotas sociales
                        periodo_mes=periodo_mes,
                        periodo_anio=periodo_anio,
                    )
                    # Crear los items de la cuota social
                    if persona.get_socio():
                        for miembro in persona.socio.grupo_familiar():
                            ItemCuotaSocial.objects.create(
                                cuota_social=cuota,
                                socio=miembro,
                                nombre_completo=miembro.persona.get_full_name(),
                                categoria=miembro.get_categoria(),
                                cuota=miembro.get_categoria().cuota,
                            )
                    else:
                        for miembro in persona.persona_set.all():
                            if miembro.get_socio() and miembro.get_socio().date_created <= \
                                    datetime(int(periodo_anio), int(periodo_mes), 1,
                                             tzinfo=pytz.timezone(settings.TIME_ZONE)):
                                ItemCuotaSocial.objects.create(
                                    cuota_social=cuota,
                                    socio=miembro,
                                    nombre_completo=miembro.get_full_name(),
                                    categoria=miembro.socio.get_categoria(),
                                    cuota=miembro.socio.get_categoria().cuota,
                                )
                    # Crear el total de la cuota social
                    total = 0
                    for item in cuota.itemcuotasocial_set.all():
                        total += item.cuota.__float__()
                    cuota.total = total
                    cuota.save()
            messages.success(request, 'Cuotas sociales generadas correctamente')
        except Exception as e:
            data['error'] = e.args[0]
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
        cuota.delete()
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
