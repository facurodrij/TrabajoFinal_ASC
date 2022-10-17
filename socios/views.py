from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

# TODO: Crear las vistas para el listado de socios,
#       el detalle de un socio, la creación de un socio,
#       la edición de un socio y la eliminación de un socio.
#       Para ello, se deben crear las clases de vistas
#       correspondientes y los templates necesarios.

from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import SocioIndividual, MiembroNoRegistrado
from .forms import *
from core.models import Club
from accounts.forms import CustomUserCreationForm, PersonaCreateForm


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


def asociacion(request):
    """ Vist para solicitar la asociación al club, solo acceden socios no registrados """
    if request.user.is_authenticated:
        messages.error(request, 'Ya estás asociado al club')
        return redirect('index')
    if request.method == 'POST':
        tipo_form = ElegirTipoForm(request.POST)
        user_form = CustomUserCreationForm(request.POST)
        persona_form = PersonaCreateForm(request.POST, request.FILES)
        if tipo_form.is_valid() and user_form.is_valid() and persona_form.is_valid():
            # Crear el usuario y persona
            try:
                user = user_form.save()
                persona = persona_form.save()
                UsuarioPersona.objects.create(user=user, persona=persona)
            except Exception as e:
                print(e)
                messages.error(request, 'Ha ocurrido un error al crear el usuario y la persona')
                return redirect('asociarse')

            # Establecer la categoria según el tipo y la edad del solicitante.
            tipo = tipo_form.cleaned_data['tipo']
            categoria = Categoria.objects.get(tipo_id=tipo,
                                              # __lte -> Less than or equal
                                              # __gte -> Greater than or equal
                                              # __lt -> Less than
                                              # __gt -> Greater than
                                              edad_desde__lte=user.get_edad(),
                                              edad_hasta__gte=user.get_edad())

            # Obtener el estado 'Falta aprobación'
            estado = Estado.objects.get(code='FA')

            # Crear el socio individual
            SocioIndividual.objects.create(user=user,
                                           club=Club.objects.first(),
                                           # TODO: Obtener el club actual.
                                           categoria=categoria,
                                           estado=estado)

            messages.success(request, 'Tu solicitud de asociación ha sido enviada, espere a que sea aprobada.')
            return redirect('login')
    else:
        tipo_form = ElegirTipoForm()
        user_form = CustomUserCreationForm()
        persona_form = PersonaCreateForm()

    context = {
        'title': 'Solicitar asociación',
        'tipo_form': tipo_form,
        'user_form': user_form,
        'persona_form': persona_form,
    }
    return render(request, 'asociacion.html', context)


class SocioIndividualDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """ Vista para el detalle de un socio individual """
    model = SocioIndividual
    template_name = 'socio_detail.html'
    permission_required = 'socios.view_socios'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle de socio'
        return context


def aprobar_socio(request, pk):
    """ Vista para aprobar un socio individual """
    if not request.user.is_admin():
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('index')
    socio = SocioIndividual.objects.get(pk=pk)
    socio.estado = Estado.objects.get(code='AP')
    socio.save()
    messages.success(request, 'Socio aprobado')
    return redirect('socios')


def rechazar_socio(request, pk):
    """ Vista para rechazar un socio individual """
    if not request.user.is_admin():
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('index')
    socio = SocioIndividual.objects.get(pk=pk)
    socio.estado = Estado.objects.get(code='RE')
    socio.save()
    messages.success(request, 'Socio rechazado')
    return redirect('socios')
