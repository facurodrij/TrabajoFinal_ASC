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
        persona_form = PersonaCreateForm(request.POST)
        if tipo_form.is_valid() and user_form.is_valid() and persona_form.is_valid():
            try:
                user = user_form.save(commit=False)
            except Exception as e:
                print(e)
                return redirect('asociarse')

            try:
                persona = persona_form.save(commit=False)
            except Exception as e:
                print(e)
                return redirect('asociarse')

            # Crear el usuario y persona
            try:
                user.save()
                persona.save()
                UsuarioPersona.objects.create(user=user, persona=persona)
            except Exception as e:
                print(e)
                return redirect('asociarse')

            # Establecer la categoria según el tipo y la edad del solicitante.
            try:
                tipo = tipo_form.cleaned_data['tipo']
                categoria = Categoria.objects.get(tipo_id=tipo,
                                                  # __lte -> Less than or equal
                                                  # __gte -> Greater than or equal
                                                  # __lt -> Less than
                                                  # __gt -> Greater than
                                                  edad_desde__lte=user.get_edad(),
                                                  edad_hasta__gte=user.get_edad())
            except Exception as e:
                messages.error(request, 'Error al obtener la categoría. ' + str(e))
                # Si hubo un error al obtener la categoria, se borra el usuario y la persona.
                UsuarioPersona.objects.get(user=user, persona=persona).hard_delete()
                user.hard_delete()
                persona.hard_delete()
                return redirect('asociarse')

            # Obtener el estado 'Falta aprobación'
            try:
                estado = Estado.objects.get(code='FA')
            except Exception as e:
                messages.error(request, 'Error al obtener el estado "Falta aprobación". ' + str(e))
                return redirect('asociarse')

            # Crear el socio individual
            try:
                SocioIndividual.objects.create(user=user,
                                               club=Club.objects.first(),
                                               # TODO: Obtener el club actual.
                                               categoria=categoria,
                                               estado=estado)
            except Exception as e:
                messages.error(request, 'Error al crear el socio. ' + str(e))
                # Si hubo un error al crear el socio, se borra el usuario y la persona.
                UsuarioPersona.objects.get(user=user, persona=persona).hard_delete()
                user.hard_delete()
                persona.hard_delete()
                return redirect('asociarse')
            messages.success(request, 'Tu solicitud de asociación ha sido enviada, espere a que sea aprobada.')
        return redirect('index')
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
