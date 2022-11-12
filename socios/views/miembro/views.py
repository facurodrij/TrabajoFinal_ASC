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
from socios.forms import MiembroForm
from socios.models import Miembro, Categoria


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
def miembro_delete(request, pk):
    """
    Eliminar un miembro
    """
    miembro = get_object_or_404(Miembro, pk=pk)
    miembro.delete(cascade=True)
    messages.success(request, 'Miembro eliminado correctamente')
    return redirect(request.META.get('HTTP_REFERER'))


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
    return redirect(request.META.get('HTTP_REFERER'))
