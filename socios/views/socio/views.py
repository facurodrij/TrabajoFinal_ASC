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
        context['title'] = 'Socios'
        return context


class SocioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """ Vista para crear un socio """
    model = Socio
    form_class = SocioForm
    template_name = 'socio/create.html'
    permission_required = 'socios.add_socio'
    success_url = reverse_lazy('socio-listado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Socio'
        context['action'] = 'add'
        context['persona_form'] = PersonaFormAdmin()
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                # Si la accion es agregar, se crea un nuevo socio
                form = self.form_class(request.POST)
                if form.is_valid():
                    with transaction.atomic():
                        socio = Socio()
                        socio.persona = form.cleaned_data['persona']
                        socio.categoria = form.cleaned_data['categoria']
                        socio.estado = form.cleaned_data['estado']
                        socio.save()
                        messages.success(request, 'Socio creado correctamente')
                else:
                    data['error'] = form.errors
            elif action == 'get_categoria':
                # Si la accion es get_categoria, se obtiene las categorias que puede tener el socio
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
            elif action == 'create_persona':
                # Si la accion es create_persona, se crea una nueva persona
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


class SocioDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """ Vista para mostrar un socio """
    model = Socio
    template_name = 'socio/detail.html'
    context_object_name = 'socio'
    permission_required = 'socios.view_socio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle de Socio'
        context['miembros'] = Miembro.objects.filter(socio=self.get_object())
        return context


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
        context['action'] = 'edit'
        context['persona_form'] = PersonaFormAdmin(instance=self.get_object().persona)
        return context

    def get_form(self, form_class=None):
        # El select de persona debe mostrar solo la persona del socio
        form = super().get_form(form_class)
        form.fields['persona'].queryset = Persona.objects.filter(pk=self.get_object().persona.pk)
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                # Si la accion es editar, se edita el socio
                form = self.form_class(request.POST, instance=self.get_object())
                if form.is_valid():
                    with transaction.atomic():
                        form.save()
                        messages.success(request, 'Socio editado correctamente')
                else:
                    data['error'] = form.errors
            elif action == 'get_categoria':
                # Si la accion es get_categoria, se obtiene las categorias que puede tener el socio
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
                # Si la accion es update_persona, se edita la persona
                persona_form = PersonaFormAdmin(request.POST, request.FILES, instance=self.get_object().persona)
                if persona_form.is_valid():
                    with transaction.atomic():
                        persona = persona_form.save()
                        data = persona.toJSON()
                        # Agregar mensaje de exito a data
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
