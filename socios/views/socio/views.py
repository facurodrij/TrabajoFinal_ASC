from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView

from accounts.decorators import admin_required
from accounts.forms import *
from core.models import Club
from socios.forms import SocioForm, MiembroForm
from socios.models import Socio, Categoria


class SocioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para listar los socios """
    model = Socio
    template_name = 'socio/list.html'
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
                        messages.success(request, 'Se ha agregado un nuevo socio')
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
            elif action == 'get_categoria':
                # Si la acción es get_categoria, se obtiene las categorias que puede tener el socio
                data = []
                # Obtener la edad de la Persona
                persona_id = request.POST['persona']
                edad = Persona.objects.get(pk=persona_id).get_edad()
                # Obtener las categorias que corresponden a la edad
                categorias = Categoria.objects.filter(edad_desde__lte=edad,
                                                      edad_hasta__gte=edad)
                for categoria in categorias:
                    item = categoria.toJSON()
                    data.append(item)
            elif action == 'edit_socio':
                # Si la acción es edit_socio, se edita un socio
                pk = request.POST['id']
                socio = Socio.objects.get(pk=pk)
                form = SocioForm(request.POST, instance=socio)
                if form.is_valid():
                    with transaction.atomic():
                        form.save()
                        data = socio.toJSON()
                else:
                    data['error'] = form.errors
            elif action == 'restore_socio_as_titular':
                # Si la acción es restore_socio_as_socio_titular, se restaura un socio como socio titular
                persona = request.POST['persona']
                categoria = request.POST['categoria']
                estado = request.POST['estado']
                with transaction.atomic():
                    socio = Socio.deleted_objects.get(persona_id=persona)
                    socio.restore()
                    socio.categoria_id = categoria
                    socio.estado_id = estado
                    socio.socio_titular_id = None
                    socio.parentesco_id = None
                    socio.save()
                    data = socio.toJSON()
                    messages.success(request, 'Se ha restaurado el socio como socio titular')
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)


class SocioDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """ Vista para mostrar un socio """
    model = Socio
    template_name = 'socio/detail.html'
    context_object_name = 'socio'
    permission_required = 'socios.view_socio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        miembro_form = MiembroForm()
        miembro_form.fields['categoria'].disabled = True
        miembro_form.fields['socio_titular'].queryset = Socio.objects.filter(pk=self.get_object().pk)
        miembro_form.fields['socio_titular'].initial = self.get_object()
        miembro_form.fields['socio_titular'].widget.attrs['hidden'] = True
        # Filtrar las personas que no sean miembros del socio
        miembro_form.fields['persona'].queryset = Persona.objects.exclude(pk=self.get_object().persona.pk).exclude(
            socio__socio_titular=self.get_object())
        context['title'] = 'Detalle de Socio'
        context['miembros'] = Socio.global_objects.filter(socio_titular=self.get_object())
        context['miembro_form'] = miembro_form
        context['persona_form'] = PersonaFormAdmin()
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add_miembro':
                # Si la acción es add_miembro, se agrega un nuevo miembro al socio
                miembro_form = MiembroForm(request.POST)
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
                else:
                    try:
                        # Si el error es por la persona
                        data['error'] = miembro_form.errors['persona'][0]
                        if Socio.objects.filter(persona_id=request.POST['persona']).exists():
                            socio = Socio.objects.get(persona_id=request.POST['persona'])
                            # Si la persona seleccionada es socio titular y tiene socios agregados, no se puede agregar
                            if socio.get_miembros().exists():
                                data['error'] = 'La persona seleccionada es socio titular y' \
                                                ' tiene miembros agregados, no se puede agregar como miembro'
                            else:
                                data['code'] = 'socio_exists'
                                data['message'] = 'La persona seleccionada es un socio,' \
                                                  ' ¿Seguro desea agregarlo como miembro?'
                    except Exception as e:
                        print(e)
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
            elif action == 'get_categoria':
                # Si la acción es get_categoria, se obtiene las categorias que puede tener el socio
                data = []
                # Obtener la edad de la Persona
                persona_id = request.POST['persona']
                edad = Persona.objects.get(pk=persona_id).get_edad()
                # Obtener las categorias que corresponden a la edad
                categorias = Categoria.objects.filter(edad_desde__lte=edad,
                                                      edad_hasta__gte=edad)
                for categoria in categorias:
                    item = categoria.toJSON()
                    data.append(item)
            elif action == 'restore_socio_as_miembro':
                # Si la acción es restore_socio, se restaura un socio eliminado
                persona = request.POST['persona']
                categoria = request.POST['categoria']
                parentesco = request.POST['parentesco']
                with transaction.atomic():
                    socio = Socio.deleted_objects.get(persona_id=persona)
                    socio.restore()
                    socio.socio_titular_id = self.get_object().pk
                    socio.categoria_id = categoria
                    socio.parentesco_id = parentesco
                    socio.save()
                    data = socio.toJSON()
                    messages.success(request, 'Socio restaurado y agregado como miembro correctamente')
            elif action == 'add_socio_as_miembro':
                # Si la acción es add_socio_as_miembro, se agrega un socio como miembro
                persona = request.POST['persona']
                categoria = request.POST['categoria']
                parentesco = request.POST['parentesco']
                with transaction.atomic():
                    socio = Socio.objects.get(persona_id=persona)
                    socio.socio_titular_id = self.get_object().pk
                    socio.estado = self.get_object().estado
                    socio.categoria_id = categoria
                    socio.parentesco_id = parentesco
                    socio.save()
                    data = socio.toJSON()
                    messages.success(request, 'Socio agregado como miembro correctamente')
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    # TODO:
    #  -Mostrar carnet de socio
    #  -Agregar miembros con ajax
    #  -Editar miembros con ajax
    #  -Eliminar miembros con ajax
    #  -Restaurar miembros con ajax


class SocioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """ Vista para editar un socio """
    model = Socio
    form_class = SocioForm
    template_name = 'socio/update.html'
    permission_required = 'socios.change_socio'
    context_object_name = 'socio'
    success_url = reverse_lazy('socio-listado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Socio'
        context['action'] = 'edit_socio'
        context['persona_form'] = PersonaFormAdmin(instance=self.get_object().persona)
        return context

    # Si el socio no es titular, cambiar form_class a MiembroForm
    def get_form_class(self):
        if self.get_object().es_titular():
            return SocioForm
        else:
            self.form_class = MiembroForm
        return MiembroForm

    def get_form(self, form_class=None):
        # El select de persona debe mostrar solo la persona del socio y deshabilitar el campo
        form = super().get_form(form_class)
        form.fields['persona'].queryset = Persona.objects.filter(pk=self.get_object().persona.pk)
        form.fields['persona'].widget.attrs['disabled'] = True
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
                # Obtener las categorias que corresponden a la edad
                categorias = Categoria.objects.filter(edad_desde__lte=edad,
                                                      edad_hasta__gte=edad)
                for categoria in categorias:
                    item = categoria.toJSON()
                    data.append(item)
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)


@login_required
@admin_required
def socio_delete(request, pk):
    """
    Eliminar un socio
    """
    socio = get_object_or_404(Socio, pk=pk)
    socio.delete(cascade=True)
    messages.success(request, 'Socio eliminado correctamente')
    return redirect('socio-listado')


@login_required
@admin_required
def socio_restore(request, pk):
    """
    Restaurar un socio eliminado
    """
    socio = Socio.deleted_objects.get(pk=pk)
    try:
        if not socio.get_related_objects():
            socio.restore()
            messages.success(request, 'Socio restaurado correctamente')
        else:
            socio.restore(cascade=True)
            messages.success(request, 'Socio y miembros restaurado correctamente')
    # Capturar el ValidationError si el socio ya existe
    except ValidationError as e:
        messages.error(request, e.message)
    return redirect('socio-listado')
