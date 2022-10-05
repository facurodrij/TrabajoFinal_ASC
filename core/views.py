from django.shortcuts import render, redirect, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required

from .models import *
from .forms import *


class IndexView(TemplateView):
    """Vista para la página de inicio."""
    template_name = 'pages/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inicio'
        return context


@login_required(login_url='login')
def club(request):
    """ Vista para el club, solo acceden superusuarios, staff y administradores del club """
    if not request.user.is_admin():
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('index')
    context = {
        'title': 'Club',
        'object': Club.objects.get(pk=1)
    }
    if request.method == 'POST':
        club_form = UpdateClubForm(request.POST, request.FILES, instance=Club.objects.get(pk=1))

        if club_form.is_valid():
            club_form.save()
            messages.success(request, 'Club actualizado exitosamente')
            return redirect(to='club')
    else:
        club_form = UpdateClubForm(instance=Club.objects.get(pk=1))

    return render(request, 'club.html', {'club_form': club_form, **context})


class SocioListView(LoginRequiredMixin, ListView):
    """ Vista para listar los socios """
    model = Socio
    template_name = 'socio_list.html'
    context_object_name = 'socios'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin():
            messages.error(request, 'No tienes permiso para acceder a esta página')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Socios'
        context['model_name'] = 'Socio'
        context['model_name_plural'] = 'Socios'
        context['all_model_deleted'] = Socio.deleted_objects.all()
        if self.request.GET.get('deleted', ''):
            """Si el parámetro deleted está presente en la URL, se obtiene el pk del club eliminado."""
            try:
                context['model_deleted'] = Socio.deleted_objects.get(pk=self.request.GET.get('deleted', ''))
            except Socio.DoesNotExist:
                print('No existe el socio eliminado')
        return context


class SocioCreateView(LoginRequiredMixin, CreateView):
    """ Vista para crear un socio """
    model = Socio
    form_class = SocioForm
    template_name = 'socio_form.html'
    success_url = reverse_lazy('socios')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin():
            messages.error(request, 'No tienes permiso para acceder a esta página')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Socio'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Socio creado exitosamente')
        return super().form_valid(form)


class SocioUpdateView(LoginRequiredMixin, UpdateView):
    """ Vista para actualizar un socio """
    model = Socio
    form_class = SocioForm
    template_name = 'socio_form.html'
    success_url = reverse_lazy('socios')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin():
            messages.error(request, 'No tienes permiso para acceder a esta página')
            return redirect('index')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Actualizar Socio'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Socio actualizado exitosamente')
        return super().form_valid(form)


def socio_delete(request, pk):
    """ Vista para eliminar un socio """
    if not request.user.is_admin():
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('index')
    Socio.objects.get(pk=pk).delete()
    # messages.success(request, 'Socio eliminado exitosamente')
    # Enviar un GET 'deleted' a la vista redirigida
    return HttpResponseRedirect(reverse_lazy('socios') + '?deleted=' + str(pk))


def socio_restore(request, pk):
    """ Vista para restaurar un socio """
    if not request.user.is_admin():
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('index')
    Socio.deleted_objects.get(pk=pk).restore()
    messages.success(request, 'Socio restaurado exitosamente')
    return redirect('socios')
