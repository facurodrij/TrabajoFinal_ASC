from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.utils.safestring import mark_safe
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six

from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import *
from .forms import *
from core.models import Club
from accounts.forms import *
from accounts.decorators import admin_required


class SocioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para listar los socios """
    model = Socio
    template_name = 'socio_list.html'
    context_object_name = 'socios'
    permission_required = 'socios.view_socio'

    def get_queryset(self):
        return Socio.global_objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Socios'
        return context


@login_required
@admin_required
def socio_create_view(request):
    """ Vista para crear un socio """
    if request.method == 'POST':
        tipo_form = ElegirTipoForm(request.POST)
        persona_form = PersonaFormAdmin(request.POST, request.FILES)
        # Usuario (opcional)
        user_form = SimpleCreateUserForm(request.POST)
        if persona_form.is_valid() and tipo_form.is_valid():
            # Crear la persona
            persona = persona_form.save(commit=False)
            persona.club = Club.objects.get(pk=1)

            # Obtener la categoría
            categoria = Categoria.objects.get(tipo_id=tipo_form.cleaned_data['tipo'],
                                              # __lte -> Less than or equal
                                              # __gte -> Greater than or equal
                                              # __lt -> Less than
                                              # __gt -> Greater than
                                              edad_desde__lte=persona.get_edad(),
                                              edad_hasta__gte=persona.get_edad())

            # Crear el socio
            try:
                socio = Socio(persona=persona,
                              categoria=categoria,
                              estado=Estado.objects.get(code='AD'))
            except IntegrityError:
                messages.error(request, 'Ya existe un socio con el DNI %s' % persona.dni)
                return redirect('socios:socio_create')

            # Si se decidió crearle un usuario al socio, se lo asigna a la persona y se envía un email
            if user_form['add_user'].value():
                if user_form.is_valid():
                    user = user_form.save(commit=False)
                    user.persona = persona
                    user.email = user_form.cleaned_data['email']
                    user.username = persona.dni
                    user.set_password(User.objects.make_random_password())
                    # Enviar email con los datos de acceso
                    current_site = get_current_site(request)
                    mail_subject = 'Bienvenido a %s' % current_site.name
                    message = render_to_string('email/socio_creado_email.html', {
                        'user': user,
                        'domain': current_site.domain,
                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                        'token': PasswordResetTokenGenerator().make_token(user),
                        'protocol': 'https' if request.is_secure() else 'http',
                    })
                    to_email = user.email
                    email = EmailMessage(mail_subject, message, to=[to_email])
                    email.send()
                    user.save()
                    persona.save()
                    socio.save()
                    messages.success(request, 'Socio creado correctamente')
                    return redirect('socios:socio_list')
                else:
                    messages.error(request, 'El usuario no es válido. ' + str(user_form.errors))
                    return redirect('socios:socio_create')
            else:  # Si no se decidió crearle un usuario al socio, se guarda la persona y el socio
                persona.save()
                socio.save()
                messages.success(request, 'Socio creado correctamente')
                return redirect('socio-listado')
    else:
        tipo_form = ElegirTipoForm()
        persona_form = PersonaFormAdmin()
        user_form = SimpleCreateUserForm()

    context = {
        'title': 'Crear socio',
        'action': 'create',
        'tipo_form': tipo_form,
        'persona_form': persona_form,
        'user_form': user_form,
    }
    return render(request, 'socio_create.html', context)


@login_required
@admin_required
def socio_detail_view(request, pk):
    """
    Vista para el detalle de un socio.
    """
    socio = get_object_or_404(Socio, pk=pk)
    context = {
        'title': 'Detalle de socio',
        'socio': socio,
    }
    return render(request, 'socio_detail.html', context)


@login_required
@admin_required
def socio_update_view(request, pk):
    """ Vista para actualizar un socio individual """
    socio = get_object_or_404(Socio, pk=pk)
    if request.method == 'POST':
        tipo_form = ElegirTipoForm(request.POST)
        estado_form = ElegirEstadoForm(request.POST)
        persona_form = PersonaFormAdmin(request.POST, request.FILES, instance=socio.persona)
        if socio.get_user() is not None:  # Si tiene usuario
            user_form = UpdateUserFormAdmin(request.POST, instance=socio.persona.user)
            if persona_form.is_valid() and tipo_form.is_valid() and estado_form.is_valid() and user_form.is_valid():
                # Actualizar la persona
                persona = persona_form.save()
                # Obtener la categoría
                categoria = Categoria.objects.get(tipo_id=tipo_form.cleaned_data['tipo'],
                                                  # __lte -> Less than or equal
                                                  # __gte -> Greater than or equal
                                                  # __lt -> Less than
                                                  # __gt -> Greater than
                                                  edad_desde__lte=persona.get_edad(),
                                                  edad_hasta__gte=persona.get_edad())
                # Actualizar el socio
                socio.categoria = categoria
                socio.estado = Estado.objects.get(nombre=estado_form.cleaned_data['estado'])
                socio.save()
                # Actualizar el usuario
                user_form.save()
                messages.success(request, 'Socio actualizado correctamente')
                return redirect('socio-detalle', pk=socio.pk)
        else:  # Si no tiene usuario asociado
            user_form = SimpleCreateUserForm(request.POST)
            if persona_form.is_valid() and tipo_form.is_valid() and estado_form.is_valid():
                # Actualizar la persona
                persona = persona_form.save()
                # Obtener la categoría
                categoria = Categoria.objects.get(tipo_id=tipo_form.cleaned_data['tipo'],
                                                  # __lte -> Less than or equal
                                                  # __gte -> Greater than or equal
                                                  # __lt -> Less than
                                                  # __gt -> Greater than
                                                  edad_desde__lte=persona.get_edad(),
                                                  edad_hasta__gte=persona.get_edad())
                # Actualizar el socio
                socio.categoria = categoria
                socio.estado = Estado.objects.get(nombre=estado_form.cleaned_data['estado'])
                socio.save()
                # Si se decidió crearle un usuario al socio, se lo asigna a la persona y se envía un email
                if user_form['add_user'].value():
                    if user_form.is_valid():
                        user = user_form.save(commit=False)
                        user.persona = persona
                        user.email = user_form.cleaned_data['email']
                        user.username = persona.dni
                        user.set_password(User.objects.make_random_password())
                        # Enviar email con los datos de acceso
                        current_site = get_current_site(request)
                        mail_subject = 'Bienvenido a %s' % current_site.name
                        message = render_to_string('email/socio_creado_email.html', {
                            'user': user,
                            'domain': current_site.domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': PasswordResetTokenGenerator().make_token(user),
                            'protocol': 'https' if request.is_secure() else 'http',
                        })
                        to_email = user.email
                        email = EmailMessage(mail_subject, message, to=[to_email])
                        email.send()
                        user.save()
                        messages.success(request, 'Socio actualizado correctamente y usuario creado')
                        return redirect('socio-detalle', pk=socio.pk)
                    else:
                        messages.error(request, 'Error al crear el usuario' + str(user_form.errors))
                        return redirect('socio-editar', pk=socio.pk)
                messages.success(request, 'Socio actualizado correctamente')
                return redirect('socio-detalle', pk=socio.pk)
    else:
        tipo_form = ElegirTipoForm(initial={'tipo': socio.categoria.tipo.pk})
        estado_form = ElegirEstadoForm(initial={'estado': socio.estado.pk})
        persona_form = PersonaFormAdmin(instance=socio.persona)
        if socio.get_user() is not None:
            user_form = UpdateUserFormAdmin(instance=socio.get_user())
        else:
            user_form = SimpleCreateUserForm()

    context = {
        'title': 'Actualizar socio',
        'action': 'update',
        'tipo_form': tipo_form,
        'estado_form': estado_form,
        'user_form': user_form,
        'persona_form': persona_form,
        'socio': socio,
    }
    return render(request, 'socio_update.html', context)
