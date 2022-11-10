import json
import six
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import EmailMessage
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, HttpResponseRedirect, get_object_or_404
from django.template.loader import render_to_string, get_template
from django.urls import reverse_lazy, reverse
from django.utils.safestring import mark_safe
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView

from socios.models import Socio, Miembro, Categoria, Estado
from socios.forms import SocioForm, SelectCategoriaForm, SelectEstadoForm, SelectParentescoForm, MiembroForm
from core.models import Club
from accounts.forms import *
from accounts.decorators import admin_required


class MiembroListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para listar los miembros """
    model = Miembro
    template_name = 'miembro/list.html'
    context_object_name = 'miembros'
    permission_required = 'socios.view_miembro'

    def get_queryset(self):
        return Miembro.global_objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Miembros'
        context['socios'] = Socio.objects.all()
        return context


class MiembroCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """ Vista para crear un miembro """
    model = Miembro
    form_class = MiembroForm
    template_name = 'miembro/create.html'
    permission_required = 'socios.add_miembro'
    context_object_name = 'miembro'
    success_url = reverse_lazy('socio-listado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Agregar Miembro'
        context['action'] = 'add'
        context['persona_form'] = PersonaFormAdmin()
        return context

    def get_form(self, form_class=None):
        form = super(MiembroCreateView, self).get_form()
        # Deshabilitar el campo socio, categoria y parentesco
        form.fields['socio'].disabled = True
        form.fields['categoria'].disabled = True
        form.fields['parentesco'].disabled = True
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                # Si la acción es agregar, se crea el miembro
                form = self.form_class(request.POST)
                if form.is_valid():
                    with transaction.atomic():
                        miembro = form.save(commit=False)
                        miembro.socio = Socio.objects.get(pk=request.POST['socio'])
                        miembro.save()
                        messages.success(request, 'Miembro agregado correctamente')
                else:
                    data['error'] = form.errors
            elif action == 'get_categoria':
                # Si la acción es get_categoria, se obtiene las categorias que puede tener el miembro
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
            elif action == 'get_socio':
                # Si la acción es get_socio, se obtiene los socios que puede tener el miembro
                data = []
                # Obtener el pk de la Persona
                persona_id = request.POST['persona']
                socios = Socio.objects.exclude(persona__pk=persona_id)
                for socio in socios:
                    item = socio.toJSON()
                    data.append(item)
            elif action == 'create_persona':
                # Si la acción es create_persona, se crea una nueva persona
                persona_form = PersonaFormAdmin(request.POST, request.FILES)
                if persona_form.is_valid():
                    with transaction.atomic():
                        persona = persona_form.save(commit=False)
                        persona.club = Club.objects.get(pk=1)
                        persona.save()
                        data = persona.toJSON()
                        # Agregar mensaje de exito a data
                        data['tags'] = 'success'
                        data['message'] = 'Persona creada correctamente'
                else:
                    data['error'] = persona_form.errors
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)


class MiembroDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """ Vista para ver un miembro """
    model = Miembro
    template_name = 'miembro/detail.html'
    permission_required = 'socios.view_miembro'
    context_object_name = 'miembro'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle de Miembro'
        return context

    # TODO:
    #  -Mostrar carnet de miembro


class MiembroUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """ Vista para editar un miembro """
    model = Miembro
    form_class = MiembroForm
    template_name = 'miembro/update.html'
    permission_required = 'socios.change_miembro'
    context_object_name = 'miembro'
    success_url = reverse_lazy('miembro-listado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Miembro'
        context['action'] = 'edit'
        context['persona_form'] = PersonaFormAdmin(instance=self.get_object().persona)
        return context

    def get_form(self, form_class=None):
        # El select de persona debe mostrar solo la persona del miembro y deshabilitar el campo
        form = super().get_form(form_class)
        form.fields['persona'].queryset = Persona.objects.filter(pk=self.get_object().persona.pk)
        form.fields['persona'].widget.attrs['disabled'] = True
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                # Si la acción es editar, se edita el miembro
                form = self.form_class(request.POST, instance=self.get_object())
                if form.is_valid():
                    with transaction.atomic():
                        form.save()
                        messages.success(request, 'Miembro editado correctamente')
                else:
                    data['error'] = form.errors
            elif action == 'get_categoria':
                # Si la acción es get_categoria, se obtiene las categorias que puede tener el miembro
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
            elif action == 'update_persona':
                # Si la acción es update_persona, se edita la persona
                persona_form = PersonaFormAdmin(request.POST, request.FILES, instance=self.get_object().persona)
                if persona_form.is_valid():
                    with transaction.atomic():
                        persona = persona_form.save()
                        data = persona.toJSON()
                        # Agregar mensaje de éxito a data
                        data['tags'] = 'success'
                        data['message'] = 'Persona editada correctamente'
                else:
                    data['error'] = persona_form.errors
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)


@login_required
@admin_required
def miembro_create_view(request, pk):
    """
    Vista para crear un miembro con un socio asignado
    """


@login_required
@admin_required
def miembro_update_view(request, miembro_pk):
    """
    Vista para actualizar un miembro
    """
    miembro = get_object_or_404(Miembro, pk=miembro_pk)
    socio = miembro.socio
    if request.method == 'POST':
        persona_form = PersonaFormAdmin(request.POST, request.FILES, instance=miembro.persona)
        categoria_form = SelectCategoriaForm(request.POST)
        parentesco_form = SelectParentescoForm(request.POST)
        if persona_form.is_valid() and categoria_form.is_valid() and parentesco_form.is_valid():
            # Actualizar la persona
            persona = persona_form.save()
            # Actualizar el miembro
            miembro.parentesco_id = parentesco_form['parentesco'].value()
            miembro.categoria_id = categoria_form['categoria'].value()
            miembro.save()
            messages.success(request, 'Miembro actualizado correctamente')
            return redirect('miembro-detalle', miembro_pk=miembro.pk)
    else:
        persona_form = PersonaFormAdmin(instance=miembro.persona)
        categoria_form = SelectCategoriaForm(initial={'categoria': miembro.categoria.pk})
        parentesco_form = SelectParentescoForm(initial={'parentesco': miembro.parentesco.pk})
    context = {
        'title': 'Actualizar miembro',
        'action': 'update',
        'persona_form': persona_form,
        'categoria_form': categoria_form,
        'parentesco_form': parentesco_form,
        'socio': socio,
        'miembro': miembro,
    }
    return render(request, 'miembro_update.html', context)


@login_required
@admin_required
def miembro_delete(request, pk):
    """
    Eliminar un miembro
    """
    miembro = get_object_or_404(Miembro, pk=pk)
    miembro.delete(cascade=True)
    messages.success(request, 'Miembro eliminado correctamente')
    return redirect('miembro-listado')


@login_required
@admin_required
def miembro_restore(request, pk):
    """
    Restaurar un miembro eliminado
    """
    miembro = Miembro.deleted_objects.get(pk=pk)
    try:
        if not miembro.get_related_objects():
            miembro.restore()
            messages.success(request, 'Miembro restaurado correctamente')
        else:
            miembro.restore(cascade=True)
            messages.success(request, 'Miembro restaurado correctamente')
    except ValidationError as e:
        messages.error(request, e.message)
    return redirect('miembro-listado')
