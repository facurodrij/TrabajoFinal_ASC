from django.shortcuts import render, redirect, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import *
from .forms import *


class IndexView(TemplateView):
    """Vista para la página de inicio."""
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inicio'
        return context


class ClubListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar los clubs."""
    model = Club
    template_name = 'club_list.html'
    permission_required = 'core.view_club'
    permission_denied_message = 'No tiene permiso para ver la lista de clubes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de clubes'
        context['clubs_deleted'] = Club.deleted_objects.all()
        if self.request.GET.get('deleted', ''):
            """Si el parámetro deleted está presente en la URL, se obtiene el pk del club eliminado."""
            try:
                context['club_deleted'] = Club.deleted_objects.get(pk=self.request.GET.get('deleted', ''))
            except Club.DoesNotExist:
                print('No existe el club eliminado')
        return context


class ClubCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear un club."""
    model = Club
    template_name = 'club_form.html'
    form_class = ClubForm
    permission_required = 'core.add_club'
    permission_denied_message = 'No tiene permiso para crear un club'
    success_url = reverse_lazy('club_list')

    # Success message
    def form_valid(self, form):
        messages.success(self.request, 'Club creado exitosamente')
        return super(ClubCreateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Club'
        return context


class ClubUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para actualizar un club."""
    model = Club
    form_class = ClubForm
    template_name = 'club_form.html'
    permission_required = 'core.change_club'
    permission_denied_message = 'No tiene permiso para actualizar un club'
    success_url = reverse_lazy('club_list')

    # Success message
    def form_valid(self, form):
        messages.success(self.request, 'Club actualizado exitosamente')
        return super(ClubUpdateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Actualizar Club'
        return context


def club_delete(request, pk):
    """Vista para eliminar un club y pasar el pk a la vista redirigida."""
    club = Club.objects.get(pk=pk)
    club.delete()
    # Enviar un GET 'deleted' a la vista redirigida
    return HttpResponseRedirect(reverse_lazy('club_list') + '?deleted=' + str(pk))


def club_restore(request, pk):
    """Vista para restaurar un club y pasar el pk a la vista redirigida."""
    club = Club.deleted_objects.get(pk=pk)
    club.restore()
    return HttpResponseRedirect(reverse_lazy('club_list'))
