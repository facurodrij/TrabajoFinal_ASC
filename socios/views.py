from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
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

from .models import SocioIndividual, MiembroNoRegistrado
from .forms import *
from core.models import Club
from accounts.forms import *
from accounts.decorators import admin_required


def send_evaluation_email(request, socio, mail_subject, template):
    """
    Función para enviar la evaluación de un socio a su correo electrónico.
    """
    current_site = get_current_site(request)
    message = render_to_string(template, {
        'user': socio.user,
        'club': socio.club,
        'domain': current_site.domain,
        'protocol': 'https' if request.is_secure() else 'http',
    })
    to_email = socio.user.email
    email = EmailMessage(
        mail_subject, message, to=[to_email]
    )
    email.send()


def send_creation_email(request, socio, mail_subject, template):
    """
    Función para enviar el correo de creación de un usuario a su correo electrónico.
    """
    current_site = get_current_site(request)
    message = render_to_string(template, {
        'user': socio.user,
        'club': socio.club,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(socio.user.pk)),
        'token': PasswordResetTokenGenerator().make_token(socio.user),
        'protocol': 'https' if request.is_secure() else 'http',
    })
    to_email = socio.user.email
    email = EmailMessage(
        mail_subject, message, to=[to_email]
    )
    email.send()


@login_required
@admin_required
def socios(request):
    """ Vista para el listado de socios, solo acceden superusuarios, staff y administradores del club """
    context = {
        'title': 'Socios',
        'socios_registrados': SocioIndividual.objects.all(),
        'socios_no_registrados': MiembroNoRegistrado.objects.all()
    }
    return render(request, 'socio_list.html', context)


@login_required
def asociarse(request):
    """ Vista para asociarse al club, solo acceden los usuarios no asociados """
    if request.user.is_socio():
        messages.error(request, 'No puede acceder a esta página porque ya es socio')
        return redirect('index')
    if request.method == 'POST':
        tipo_form = ElegirTipoForm(request.POST)
        persona_form = PersonaCreateForm(request.POST, request.FILES)
        if tipo_form.is_valid() and persona_form.is_valid():
            # Crear el usuario y persona
            user = request.user
            persona = persona_form.save()
            try:
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
        persona_form = PersonaCreateForm()

    context = {
        'title': 'Solicitar asociación',
        'tipo_form': tipo_form,
        'persona_form': persona_form,
    }
    return render(request, 'asociarse.html', context)


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


@admin_required
def aprobar_socio(request, pk):
    """ Vista para aprobar un socio individual """
    socio = SocioIndividual.objects.get(pk=pk)
    socio.estado = Estado.objects.get(code='AP')
    socio.save()
    send_evaluation_email(request, socio, 'Solicitud de asociación aprobada', 'email/socio_aprobado.html')
    messages.success(request, 'Socio aprobado correctamente')
    return redirect('socios')


@admin_required
def rechazar_socio(request, pk):
    """ Vista para rechazar un socio individual """
    if not request.user.is_admin():
        messages.error(request, 'No tienes permiso para acceder a esta página')
        return redirect('index')
    socio = SocioIndividual.objects.get(pk=pk)
    socio.estado = Estado.objects.get(code='RE')
    socio.save()
    send_evaluation_email(request, socio, 'Solicitud de asociación rechazada', 'email/socio_rechazado.html')
    messages.success(request, 'Socio rechazado correctamente')
    return redirect('socios')


@login_required
@admin_required
def crear_socio(request):
    """ Vista para crear un socio individual """
    if request.method == 'POST':
        tipo_form = ElegirTipoForm(request.POST)
        user_form = BasicUserCreationForm(request.POST)
        persona_form = PersonaCreateForm(request.POST, request.FILES)
        if user_form.is_valid() and persona_form.is_valid() and tipo_form.is_valid():
            # Crear el usuario y persona
            try:
                username = user_form.cleaned_data['username']
                email = user_form.cleaned_data['email']
                password = User.objects.make_random_password()
                user = User.objects.create_user(username=username, email=email, password=password)
            except Exception as e:
                # Si el usuario ya existe, se muestra un mensaje de error.
                messages.error(request, 'Error al crear el usuario: ' + str(e))
                return redirect('socio-crear')
            persona = persona_form.save()
            try:
                UsuarioPersona.objects.create(user=user, persona=persona)
            except Exception as e:
                messages.error(request, 'Ha ocurrido un error al crear el usuario y la persona: ' + str(e))
                return redirect('socio-crear')

            # Establecer la categoria según el tipo y la edad del solicitante.
            tipo = tipo_form.cleaned_data['tipo']
            categoria = Categoria.objects.get(tipo_id=tipo,
                                              # __lte -> Less than or equal
                                              # __gte -> Greater than or equal
                                              # __lt -> Less than
                                              # __gt -> Greater than
                                              edad_desde__lte=user.get_edad(),
                                              edad_hasta__gte=user.get_edad())

            # Obtener el estado 'Aprobado'
            estado = Estado.objects.get(code='AP')

            # Crear el socio individual
            socio = SocioIndividual.objects.create(user=user,
                                                   club=Club.objects.first(),
                                                   # TODO: Obtener el club actual.
                                                   categoria=categoria,
                                                   estado=estado)
            # Enviar el email de bienvenida al socio.
            send_creation_email(request, socio, 'Bienvenido socio al club', 'email/socio_creado.html')
            messages.success(request, 'Socio creado correctamente')
            return redirect('socios')
    else:
        tipo_form = ElegirTipoForm()
        user_form = BasicUserCreationForm()
        persona_form = PersonaCreateForm()

    context = {
        'title': 'Crear socio',
        'tipo_form': tipo_form,
        'user_form': user_form,
        'persona_form': persona_form,
    }
    return render(request, 'socio_create.html', context)


def actualizar_socio(request, pk):
    """ Vista para actualizar un socio individual """
    socio = SocioIndividual.objects.get(pk=pk)
    if request.method == 'POST':
        user_form = CustomUserChangeForm(request.POST, instance=socio.user)
        persona_form = PersonaChangeForm(request.POST, request.FILES, instance=socio.user.usuariopersona.persona)
        if user_form.is_valid() and persona_form.is_valid():
            # Actualizar el usuario y persona
            user = user_form.save()
            persona = persona_form.save()
            messages.success(request, 'Socio actualizado correctamente')
            return redirect('socio-detalle', pk=socio.pk)
    else:
        user_form = CustomUserChangeForm(instance=socio.user)
        persona_form = PersonaChangeForm(instance=socio.user.usuariopersona.persona)

    context = {
        'title': 'Actualizar socio',
        'user_form': user_form,
        'persona_form': persona_form,
    }
    return render(request, 'socio_update.html', context)
