from datetime import datetime, date

import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView
from weasyprint import HTML, CSS

from accounts.forms import *
from core.models import Club
from parameters.models import SociosParameters
from socios.forms import SocioForm, CuotaSocialForm
from socios.models import Socio, Categoria, CuotaSocial, DetalleCuotaSocial
from socios.utilities import get_categoria


class SocioAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para listar los socios """
    model = Socio
    template_name = 'admin/socio/list.html'
    context_object_name = 'socios'
    permission_required = 'socios.view_socio'

    def get_queryset(self):
        return Socio.global_objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de socios'
        socio_form = SocioForm()
        socio_form.fields['categoria'].disabled = True
        context['socio_form'] = socio_form
        context['persona_form'] = PersonaFormAdmin()
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add_socio':
                # Si la acción es add_socio, se crea un nuevo socio
                form = SocioForm(request.POST)
                if form.is_valid():
                    with transaction.atomic():
                        # Si la persona seleccionada es socio, pero está eliminado
                        persona = form.cleaned_data['persona']
                        if Socio.deleted_objects.filter(persona=persona).exists():
                            data['code'] = 'socio_deleted_exists'
                            data['message'] = 'La persona seleccionada es un socio pero está eliminado,' \
                                              ' ¿Desea restaurarlo y convertirlo en socio titular?'
                        form.save()
                        data['id'] = form.instance.id
                        data['history_id'] = form.instance.history.first().pk
                else:
                    data['error'] = form.errors
            elif action == 'add_persona':
                # Si la acción es add_persona, se crea una nueva persona
                form = PersonaFormAdmin(request.POST, request.FILES)
                if form.is_valid():
                    with transaction.atomic():
                        persona = form.save(commit=False)
                        persona.club = Club.objects.get(pk=1)
                        persona.save()
                        data = persona.toJSON()
                else:
                    data['error'] = form.errors
            elif action == 'select_persona_change':
                data = get_categoria(persona=request.POST['persona'])
                edad_minima_titular = SociosParameters.objects.get(club_id=1).edad_minima_socio_titular
                # Si la persona es menor de edad_minima_titular, mandar una variable
                # tutor_required para que el front-end sepa que debe pedir
                edad = Persona.objects.get(pk=request.POST['persona']).get_edad()
                tutor_required = True if edad < edad_minima_titular else False
                data.append({'tutor_required': tutor_required})
            elif action == 'restore_socio_from_modal':
                # Si la acción es restore_socio_from_modal, si el socio es mayor de
                # edad_minima_titular años se lo restaura como titular, si no se lo
                # restaura como miembro, con los datos enviados desde el modal.
                persona = request.POST['persona']
                categoria = request.POST['categoria']
                socio_titular = request.POST['socio_titular']
                parentesco = request.POST['parentesco']
                socio = Socio.deleted_objects.get(persona_id=persona)
                edad_minima_titular = SociosParameters.objects.get(club_id=1).edad_minima_socio_titular
                with transaction.atomic():
                    socio.restore()
                    socio.categoria_id = categoria
                    if socio.persona.get_edad() < edad_minima_titular:
                        socio.socio_titular_id = socio_titular
                        socio.parentesco_id = parentesco
                        socio.save()
                        data = socio.toJSON()
                        messages.success(request, 'Se ha restaurado el socio como socio miembro')
                    else:
                        socio.socio_titular_id = None
                        socio.parentesco_id = None
                        socio.save()
                        data = socio.toJSON()
                        messages.success(request, 'Se ha restaurado el socio como socio titular')
                    data['history_id'] = socio.history.first().pk
            elif action == 'delete_socio':
                # Si la acción es delete_socio, se elimina el socio
                socio = Socio.objects.get(pk=request.POST['id'])
                motivo = request.POST['motivo']
                with transaction.atomic():
                    socio._change_reason = motivo
                    socio.delete(cascade=True)
                    data['id'] = request.POST['id']
                    data['history_id'] = socio.history.first().pk
            elif action == 'restore_socio':
                # Si la acción es restore_socio, se restaura el socio
                socio = Socio.deleted_objects.get(pk=request.POST['id'])
                with transaction.atomic():
                    if not socio.get_related_objects():
                        edad_minima_titular = SociosParameters.objects.get(club_id=1).edad_minima_socio_titular
                        socio.restore()
                        if socio.es_titular() and socio.persona.get_edad() < edad_minima_titular:
                            raise ValidationError(
                                'El socio que intenta restaurar es menor de {} años y no tiene tutor a cargo. '
                                'Agréguelo manualmente con un titular a cargo.'.format(edad_minima_titular))
                        if not socio.es_titular() and socio.socio_titular.is_deleted:
                            if socio.persona.get_edad() < edad_minima_titular:
                                raise ValidationError(
                                    'El socio que intenta restaurar es menor de {} años y no tiene tutor a cargo '
                                    'activo. Agréguelo manualmente con un titular a cargo.'.format(edad_minima_titular))
                            else:
                                raise ValidationError(
                                    'El socio titular del miembro que intenta restaurar está eliminado. '
                                    'Agréguelo manualmente como titular o como miembro de un titular activo.')
                        data['id'] = request.POST['id']
                        data['history_id'] = socio.history.first().pk
                    else:
                        socio.restore(cascade=True)
                        data['id'] = request.POST['id']
                        data['history_id'] = socio.history.first().pk
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = str(e)
        print('SocioAdminListView: POST data: ', data)
        return JsonResponse(data, safe=False)


class SocioAdminDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """ Vista para mostrar un socio, solo para administradores """
    model = Socio
    template_name = 'admin/socio/detail.html'
    context_object_name = 'socio'
    permission_required = 'socios.view_socio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        miembro_form = SocioForm()
        miembro_form.fields['categoria'].disabled = True
        miembro_form.fields['socio_titular'].queryset = Socio.objects.filter(pk=self.get_object().pk)
        miembro_form.fields['socio_titular'].initial = self.get_object()
        miembro_form.fields['socio_titular'].widget.attrs['hidden'] = True
        # Filtrar las personas que no sean miembros del socio
        miembro_form.fields['persona'].queryset = Persona.objects.exclude(pk=self.get_object().persona.pk).exclude(
            socio__socio_titular=self.get_object())
        context['title'] = 'Detalle de Socio'
        # Obtener los miembros del socio y el socio titular
        if self.get_object().es_titular():
            context['miembros'] = Socio.global_objects.filter(
                Q(socio_titular=self.get_object()) | Q(pk=self.get_object().pk))
        else:
            context['miembros'] = Socio.global_objects.filter(
                Q(socio_titular=self.get_object().socio_titular) | Q(pk=self.get_object().socio_titular.pk))
        context['miembro_form'] = miembro_form
        context['persona_form'] = PersonaFormAdmin()
        context['cuota_social_form'] = CuotaSocialForm()
        context['cuota_social_form'].fields['persona'].initial = self.get_object().persona
        context['cuotas_sociales'] = CuotaSocial.global_objects.filter(detallecuotasocial__socio=self.get_object())
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add_miembro':
                # Si la acción es add_miembro, se agrega un nuevo miembro al socio
                miembro_form = SocioForm(request.POST)
                if miembro_form.is_valid():
                    with transaction.atomic():
                        # Si la persona seleccionada es socio titular, pero está eliminado
                        persona = miembro_form.cleaned_data['persona']
                        if Socio.deleted_objects.filter(persona=persona).exists():
                            data['code'] = 'socio_deleted_exists'
                            data['message'] = 'La persona seleccionada es un socio pero está eliminado,' \
                                              ' ¿Desea restaurarlo y agregarlo como miembro?'
                        miembro_form.save()
                        messages.success(request, 'Miembro agregado correctamente')
                        data['id'] = miembro_form.instance.id
                        data['history_id'] = miembro_form.instance.history.first().pk
                else:
                    data['error'] = miembro_form.errors
            elif action == 'add_persona':
                # Si la acción es create_persona, se crea una nueva persona
                persona_form = PersonaFormAdmin(request.POST, request.FILES)
                if persona_form.is_valid():
                    with transaction.atomic():
                        persona = persona_form.save(commit=False)
                        persona.club = Club.objects.get(pk=1)
                        persona.save()
                        data = persona.toJSON()
                else:
                    data['error'] = persona_form.errors
            elif action == 'select_persona_change':
                data = get_categoria(persona=request.POST['persona'])
            elif action == 'restore_socio_as_miembro':
                # Si la acción es restore_socio, se restaura un socio eliminado
                persona = request.POST['persona']
                categoria = request.POST['categoria']
                parentesco = request.POST['parentesco']
                with transaction.atomic():
                    socio = Socio.deleted_objects.get(persona_id=persona)
                    socio.restore()
                    # Si tenia miembros agregados, se eliminan
                    if socio.get_miembros().exists():
                        for miembro in socio.get_miembros():
                            miembro.socio_titular_id = None
                            miembro.parentesco_id = None
                            miembro.delete()
                    socio.socio_titular_id = self.get_object().pk
                    socio.categoria_id = categoria
                    socio.parentesco_id = parentesco
                    socio.save()
                    data = socio.toJSON()
                    data['history_id'] = socio.history.first().pk
            elif action == 'delete_socio':
                # Si la acción es delete_socio, se elimina el socio
                socio = Socio.objects.get(pk=request.POST['id'])
                motivo = request.POST['motivo']
                with transaction.atomic():
                    socio._change_reason = motivo
                    socio.delete(cascade=True)
                    data['id'] = request.POST['id']
                    data['history_id'] = socio.history.first().pk
                    if socio.es_titular():
                        data['success_url'] = reverse_lazy('admin-socio-listado')
                        messages.success(request, 'Socio eliminado correctamente')
            elif action == 'restore_socio':
                # Si la acción es restore_socio, se restaura el miembro
                socio = Socio.deleted_objects.get(pk=request.POST['id'])
                with transaction.atomic():
                    socio.restore()
                    data['id'] = request.POST['id']
                    data['history_id'] = socio.history.first().pk
            elif action == 'add_cuota_social':
                # Si la acción es add_cuota_social, se agregan las cuotas sociales
                if CuotaSocialForm(request.POST).is_valid():
                    periodo_mes = request.POST.getlist('meses')
                    with transaction.atomic():
                        for mes in periodo_mes:
                            cuota_social = CuotaSocialForm(request.POST).save(commit=False)
                            cuota_social.periodo_mes = mes
                            # fecha_emision = datetime.now con timezone de argentina
                            cuota_social.fecha_emision = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
                            parameters_dia_vencimiento = SociosParameters.objects.get(pk=1).dia_vencimiento_cuota
                            cuota_social.fecha_vencimiento = date(int(cuota_social.periodo_anio),
                                                                  int(cuota_social.periodo_mes),
                                                                  int(parameters_dia_vencimiento))
                            cuota_social.save()
                            # Agregar el detalle de la cuota social
                            detalle = DetalleCuotaSocial()
                            detalle.cuota_social = cuota_social
                            detalle.socio = self.get_object()
                            detalle.nombre_completo = self.get_object().persona.get_full_name()
                            detalle.categoria = self.get_object().categoria.__str__()
                            detalle.save()
                            for miembro in self.get_object().get_miembros():
                                detalle_miembro = DetalleCuotaSocial()
                                detalle_miembro.cuota_social = cuota_social
                                detalle_miembro.socio = miembro
                                detalle_miembro.nombre_completo = miembro.persona.get_full_name()
                                detalle_miembro.categoria = miembro.categoria.__str__()
                                detalle_miembro.save()
                            # Generar el total, sumando los totales parciales de los detalles relacionados.
                            total = cuota_social.cargo_extra
                            for detalle in cuota_social.detallecuotasocial_set.all():
                                total += detalle.total_parcial
                            cuota_social.total = total
                            cuota_social.save()
                        messages.success(request, 'Cuota/s social/es agregada/s correctamente')
                else:
                    data['error'] = CuotaSocialForm(request.POST).errors
            elif action == 'mark_as_paid':
                # Si la acción es mark_as_paid, se marca una cuota social como pagada
                # TODO: Actualizar la acción mark_as_paid para que se pueda marcar como pagada una cuota social
                aumento_por_cuota_vencida = SociosParameters.objects.get(pk=1).aumento_por_cuota_vencida
                cuota_social_id = request.POST['id']
                cuota_social = CuotaSocial.objects.get(pk=cuota_social_id)
                # Calcular intereses
                if cuota_social.fecha_vencimiento < datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')):
                    # Calcular los meses de atraso
                    meses_atraso = (datetime.now(pytz.timezone(
                        'America/Argentina/Buenos_Aires')).year - cuota_social.fecha_vencimiento.year) * 12 + (
                                               datetime.now(pytz.timezone(
                                                   'America/Argentina/Buenos_Aires')).month - cuota_social.fecha_vencimiento.month)
                    interes = cuota_social.total * (aumento_por_cuota_vencida / 100) * meses_atraso
                with transaction.atomic():
                    cuota_social.pagada = True
                    cuota_social.fecha_pago = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
                    cuota_social.cargo_extra += interes
                    if interes > 0:
                        cuota_social.observaciones += 'Intereses por atraso: $' + str(interes)
                    cuota_social.save()
                    data['id'] = request.POST['id']
                    data['history_id'] = cuota_social.history.first().pk
                periodo = date(int(cuota_social.periodo_anio), int(cuota_social.periodo_mes), 1)
                # Aumentar el total_pagado. Por cada mes pasado desde el mes de fecha_vencimiento, se aumenta el total_pagado
                # en el porcentaje de aumento_por_cuota_vencida
                total_pagado = cuota_social.total
                if cuota_social.fecha_vencimiento < date.today():
                    meses_vencidos = (date.today().year - cuota_social.fecha_vencimiento.year) * 12 + \
                                     date.today().month - cuota_social.fecha_vencimiento.month
                    total_pagado += total_pagado * (aumento_por_cuota_vencida / 100) * meses_vencidos
                cuota_social.fecha_pago = datetime.now()
                cuota_social.total_pagado = total_pagado
                cuota_social.save()
                messages.success(request, 'Cuota social marcada como pagada correctamente')
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = str(e)
        print('SocioAdminDetailView: POST data: ', data)
        return JsonResponse(data, safe=False)


class SocioAdminUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """ Vista para editar un socio, solo para administradores """
    model = Socio
    form_class = SocioForm
    template_name = 'admin/socio/update.html'
    permission_required = 'socios.change_socio'
    context_object_name = 'socio'
    success_url = reverse_lazy('admin-socio-listado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Socio'
        context['action'] = 'edit_socio'
        context['persona_form'] = PersonaFormAdmin(instance=self.get_object().persona)
        context['socio_titular_id'] = self.get_object().socio_titular_id
        return context

    def get_form(self, form_class=None):
        # El select de persona debe mostrar solo la persona del socio y deshabilitar el campo
        form = super().get_form(form_class)
        form.fields['persona'].queryset = Persona.objects.filter(pk=self.get_object().persona.pk)
        form.fields['persona'].widget.attrs['disabled'] = True
        if self.get_object().es_titular():
            # Quitar el campo socio_titular y parentesco
            del form.fields['socio_titular']
            del form.fields['parentesco']
        # Si el socio no es titular, el select de socio_titular debe mostrar solo su socio titular
        if not self.get_object().es_titular():
            form.fields['socio_titular'].queryset = Socio.objects.filter(pk=self.get_object().socio_titular.pk)
            form.fields['socio_titular'].widget.attrs['disabled'] = True
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit_socio':
                # Si la acción es editar, se edita el socio
                form = self.get_form_class()(request.POST, instance=self.get_object())
                if form.is_valid():
                    with transaction.atomic():
                        form.save()
                        messages.success(request, 'Socio editado correctamente')
                else:
                    data['error'] = form.errors
            elif action == 'edit_persona':
                # Si la acción es update_persona, se edita la persona
                persona_form = PersonaFormAdmin(request.POST, request.FILES, instance=self.get_object().persona)
                if persona_form.is_valid():
                    with transaction.atomic():
                        persona = persona_form.save()
                        data = persona.toJSON()
                else:
                    data['error'] = persona_form.errors
            elif action == 'get_categoria':
                # Si la acción es get_categoria, se obtiene las categorias que puede tener el socio
                data = []
                # Obtener la edad de la Persona
                persona_id = request.POST['persona']
                edad = Persona.objects.get(pk=persona_id).get_edad()
                # Obtener las categorias que corresponden a la edad, incluyendo la primera categoria
                categorias = Categoria.objects.filter((Q(edad_desde__lte=edad) & Q(edad_hasta__gte=edad)) | Q(pk=1))
                for categoria in categorias:
                    item = categoria.toJSON()
                    data.append(item)
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)


def socio_history_pdf(request, socio_pk, history_pk):
    socio = Socio.global_objects.get(pk=socio_pk)
    club = Club.objects.get(pk=1)
    history = socio.history.get(pk=history_pk)
    html_string = render_to_string('admin/socio/history_pdf.html', {'history': history,
                                                                    'socio': socio,
                                                                    'club': club})
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    html.write_pdf(target='/tmp/socio_historial.pdf',
                   stylesheets=[CSS('{}/libs/bootstrap-4.6.2/bootstrap.min.css'.format(settings.STATICFILES_DIRS[0]))])
    fs = FileSystemStorage('/tmp')
    with fs.open('socio_historial.pdf') as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="socio_historial.pdf"'
        return response
