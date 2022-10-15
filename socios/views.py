from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.urls import reverse_lazy, reverse

# TODO: Crear las vistas para el listado de socios,
#       el detalle de un socio, la creación de un socio,
#       la edición de un socio y la eliminación de un socio.
#       Para ello, se deben crear las clases de vistas
#       correspondientes y los templates necesarios.

from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import SocioIndividual, MiembroNoRegistrado


def socios(request):
    """ Vista para el listado de socios, solo acceden superusuarios, staff y administradores del club """
    if not request.user.is_admin():
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('index')
    context = {
        'title': 'Socios',
        'socios_registrados': SocioIndividual.objects.all(),
        'socios_no_registrados': MiembroNoRegistrado.objects.all()
    }
    return render(request, 'socio_list.html', context)
