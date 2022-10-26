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
from .mails import *
from core.models import Club
from accounts.forms import *
from accounts.decorators import admin_required


@login_required
@admin_required
def socios_view(request):
    """ Vista para el listado de socios, solo acceden superusuarios, staff y administradores del club """
    context = {
        'title': 'Socios',
        'socios': Socio.objects.all(),
    }
    return render(request, 'socio_list.html', context)


def asociarse_view(request):
    """ Vista para solicitar la asociación al club """
    if request.method == 'POST':
        tipo_form = ElegirTipoForm(request.POST)
        user_form = BasicUserCreationForm(request.POST)
        persona_form = PersonaForm(request.POST, request.FILES)
        if user_form.is_valid() and persona_form.is_valid() and tipo_form.is_valid():
            # Crear el usuario.
            user = user_form.save(commit=False)
            password = User.objects.make_random_password()
            user.set_password(password)
            user.save()

            # Crear la persona.
            persona = persona_form.save()

            # Crear la tabla UsuarioPersona.
            UsuarioPersona.objects.create(user=user, persona=persona)

            tipo = tipo_form.cleaned_data['tipo']

            # Enviar mail al administrador para que apruebe la solicitud.
            current_site = get_current_site(request)
            mail_subject = 'Solicitud de asociación'
            message = render_to_string('email/solicitud_asociación.html', {
                'user': user,
                'tipo': tipo,
                'domain': current_site.domain,
                'protocol': 'https' if request.is_secure() else 'http',
            })
            to_email = 'administrador@cabm.com.ar'
            email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            email.send()
            messages.success(request, 'Tu solicitud de asociación ha sido enviada, espere a que sea aprobada.')
            return redirect('login')
    else:
        tipo_form = ElegirTipoForm()
        user_form = BasicUserCreationForm()
        persona_form = PersonaForm()

    context = {
        'title': 'Solicitar asociación',
        'tipo_form': tipo_form,
        'user_form': user_form,
        'persona_form': persona_form,
    }
    return render(request, 'asociarse.html', context)


@login_required
@admin_required
def socio_create_view(request):
    """ Vista para crear un socio individual """
    if request.method == 'POST':
        tipo_form = ElegirTipoForm(request.POST)
        user_form = BasicUserCreationForm(request.POST)
        persona_form = PersonaForm(request.POST, request.FILES)
        if user_form.is_valid() and persona_form.is_valid() and tipo_form.is_valid():
            # Crear el usuario
            user = user_form.save(commit=False)
            password = User.objects.make_random_password()
            user.set_password(password)
            user.save()

            # Crear la persona
            persona = persona_form.save()

            # Crear la tabla UsuarioPersona
            UsuarioPersona.objects.create(user=user, persona=persona)

            # Obtener el tipo de socio elegido
            tipo = tipo_form.cleaned_data['tipo']

            # Obtener la categoría
            categoria = Categoria.objects.get(tipo_id=tipo,
                                              # __lte -> Less than or equal
                                              # __gte -> Greater than or equal
                                              # __lt -> Less than
                                              # __gt -> Greater than
                                              edad_desde__lte=user.get_edad(),
                                              edad_hasta__gte=user.get_edad())

            # Obtener el estado "Al día"
            estado = Estado.objects.get(code='AD')

            # Crear el socio
            socio = Socio.objects.create(user=user,
                                         club=Club.objects.first(),
                                         # TODO: Obtener el club actual.
                                         categoria=categoria,
                                         estado=estado)

            # Enviar el email de bienvenida al socio.
            current_site = get_current_site(request)
            mail_subject = 'Bienvenido socio al club'
            message = render_to_string('email/socio_creado.html', {
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
            messages.success(request, 'Socio creado correctamente')
            return redirect('socio-listado')
    else:
        tipo_form = ElegirTipoForm()
        user_form = BasicUserCreationForm()
        persona_form = PersonaForm()

    context = {
        'title': 'Crear socio',
        'action': 'create',
        'tipo_form': tipo_form,
        'user_form': user_form,
        'persona_form': persona_form
    }
    return render(request, 'socio_create.html', context)


@login_required
def socio_detail_view(request, pk):
    """
    Vista para el detalle de un socio. Solo puede acceder el socio o un administrador.
    """
    socio = get_object_or_404(Socio, pk=pk)
    if socio.user == request.user or request.user.is_staff:
        context = {
            'title': 'Detalle de socio',
            'socio': socio,
        }
        return render(request, 'socio_detail.html', context)
    else:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('index')


@login_required
@admin_required
def socio_update_view(request, pk):
    """ Vista para actualizar un socio individual """
    socio = get_object_or_404(Socio, pk=pk)
    if request.method == 'POST':
        tipo_form = ElegirTipoForm(request.POST)
        estado_form = ElegirEstadoForm(request.POST)
        user_form = CustomUserChangeForm(request.POST, instance=socio.user)
        persona_form = PersonaForm(request.POST, request.FILES, instance=socio.user.usuariopersona.persona)
        if user_form.is_valid() and persona_form.is_valid() and tipo_form.is_valid() and estado_form.is_valid():
            # Actualizar el usuario y persona
            tipo = tipo_form.cleaned_data['tipo']
            user = user_form.save()
            persona = persona_form.save()

            # Actualizar la categoría
            categoria = Categoria.objects.get(tipo_id=tipo,
                                              # __lte -> Less than or equal
                                              # __gte -> Greater than or equal
                                              # __lt -> Less than
                                              # __gt -> Greater than
                                              edad_desde__lte=user.get_edad(),
                                              edad_hasta__gte=user.get_edad())
            socio.categoria = categoria

            # Actualizar el estado
            estado = estado_form.cleaned_data['estado']
            socio.estado = estado

            # Guardar el socio en la base de datos
            socio.save()

            messages.success(request, 'Socio actualizado correctamente')
            return redirect('socio-detalle', pk=socio.pk)
    else:
        tipo_form = ElegirTipoForm(initial={'tipo': socio.categoria.tipo.pk})
        estado_form = ElegirEstadoForm(initial={'estado': socio.estado.pk})
        user_form = CustomUserChangeForm(instance=socio.user)
        persona_form = PersonaForm(instance=socio.user.usuariopersona.persona)

    context = {
        'title': 'Actualizar socio',
        'action': 'update',
        'tipo_form': tipo_form,
        'estado_form': estado_form,
        'user_form': user_form,
        'persona_form': persona_form,
    }
    return render(request, 'socio_update.html', context)
