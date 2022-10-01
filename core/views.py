from django.shortcuts import render, redirect, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required

from .models import Club
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
