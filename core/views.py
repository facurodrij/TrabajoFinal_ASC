import pathlib
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.core import management

from .forms import *
from accounts.decorators import admin_required


class IndexView(TemplateView):
    """Vista para la página de inicio."""
    template_name = 'pages/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inicio'
        return context


@login_required(login_url='login')
@admin_required
def club(request):
    """ Vista para el club, solo acceden superusuarios, staff y administradores del club """
    try:
        club_object = Club.objects.get(pk=1)
    except Club.DoesNotExist:
        # Si no existe el club, ejecuta el comando loaddata para cargar los datos iniciales
        arg = list(pathlib.Path().glob('*/fixtures/*.json'))
        management.call_command('loaddata', *arg)
        club_object = Club.objects.get(pk=1)
        pass

    if request.method == 'POST':
        club_form = UpdateClubForm(request.POST, request.FILES, instance=club_object)

        if club_form.is_valid():
            club_form.save()
            messages.success(request, 'Club actualizado exitosamente')
            return redirect(to='club')
    else:
        club_form = UpdateClubForm(instance=club_object)

    context = {
        'title': 'Club',
        'object': club_object,
        'club_form': club_form,
    }
    return render(request, 'club.html', context)
