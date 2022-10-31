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
from django.http import JsonResponse
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
        return Socio.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Socios'
        context['socios_eliminados'] = Socio.deleted_objects.all()
        # TODO: Agregar lista de Miembros
        return context


def obtener_categorias(request):
    """ Retonar un json con las categorias de un socio segun la edad """
    if request.method == 'GET':
        edad = request.GET.get('edad', None)
        categorias = Categoria.objects.filter(edad_desde__lte=edad,
                                              edad_hasta__gte=edad)
        return JsonResponse(list(categorias.values()), safe=False)
    return HttpResponseBadRequest()


@login_required
@admin_required
def socio_create_view(request):
    """ Vista para crear un socio """
    if request.method == 'POST':
        persona_form = PersonaFormAdmin(request.POST, request.FILES)
        categoria_form = SelectCategoriaForm(request.POST)
        # Usuario (opcional)
        user_form = SimpleCreateUserForm(request.POST)
        if persona_form.is_valid():
            # Crear la persona
            persona = persona_form.save(commit=False)
            persona.club = Club.objects.get(pk=1)

            # Obtener la categoría
            categoria = categoria_form['categoria'].value()

            # Crear el socio
            socio = Socio(persona=persona,
                          categoria_id=categoria,
                          estado=Estado.objects.get(code='AD'))

            # Si se decidió crearle un usuario al socio, se lo asigna a la persona y se envía un email
            if user_form['add_user'].value():
                if user_form.is_valid():
                    user = User()
                    user.persona = persona
                    user.email = user_form.clean_email()
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
                    persona.save()
                    user.save()
                    socio.save()
                    messages.success(request, 'Socio creado correctamente')
                    return redirect('socio-detalle', pk=socio.pk)
            else:  # Si no se decidió crearle un usuario al socio, se guarda la persona y el socio
                persona.save()
                socio.save()
                messages.success(request, 'Socio creado correctamente')
                return redirect('socio-detalle', pk=socio.pk)
    else:
        persona_form = PersonaFormAdmin()
        user_form = SimpleCreateUserForm()
        categoria_form = SelectCategoriaForm()
    context = {
        'title': 'Crear socio',
        'action': 'create',
        'persona_form': persona_form,
        'user_form': user_form,
        'categoria_form': categoria_form,
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
        estado_form = SelectEstadoForm(request.POST)
        categoria_form = SelectCategoriaForm(request.POST)
        persona_form = PersonaFormAdmin(request.POST, request.FILES, instance=socio.persona)
        if socio.get_user() is not None:  # Si tiene usuario
            user_form = UpdateUserFormAdmin(request.POST, instance=socio.persona.user)
            if persona_form.is_valid() and estado_form.is_valid() and user_form.is_valid() and categoria_form.is_valid():
                # Actualizar la persona
                persona_form.save()
                # Actualizar el socio
                socio.categoria_id = categoria_form['categoria'].value()
                socio.estado_id = estado_form['estado'].value()
                socio.save()
                # Actualizar el usuario
                user_form.save()
                # TODO: Enviar email de actualización de datos

                messages.success(request, 'Socio actualizado correctamente')
                return redirect('socio-detalle', pk=socio.pk)
        else:  # Si no tiene usuario asociado
            user_form = SimpleCreateUserForm(request.POST)
            if persona_form.is_valid() and estado_form.is_valid() and categoria_form.is_valid():
                # Actualizar la persona
                persona = persona_form.save()
                # Obtener la categoría
                categoria = categoria_form['categoria'].value()
                # Actualizar el socio
                socio.categoria_id = categoria
                socio.estado_id = estado_form['estado'].value()
                socio.save()
                # Si se decidió crearle un usuario al socio, se lo asigna a la persona y se envía un email
                if user_form['add_user'].value():
                    if user_form.is_valid():
                        user = User()
                        user.persona = persona
                        user.email = user_form.clean_email()
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
                        messages.success(request, 'Socio y Usuario actualizado correctamente')
                        return redirect('socio-detalle', pk=socio.pk)
                messages.success(request, 'Socio actualizado correctamente')
                return redirect('socio-detalle', pk=socio.pk)
    else:
        estado_form = SelectEstadoForm(initial={'estado': socio.estado.pk})
        persona_form = PersonaFormAdmin(instance=socio.persona)
        categoria_form = SelectCategoriaForm(initial={'categoria': socio.categoria.pk})
        if socio.get_user() is not None:
            user_form = UpdateUserFormAdmin(instance=socio.get_user())
        else:
            user_form = SimpleCreateUserForm()

    context = {
        'title': 'Actualizar socio',
        'action': 'update',
        'estado_form': estado_form,
        'user_form': user_form,
        'persona_form': persona_form,
        'categoria_form': categoria_form,
        'socio': socio,
    }
    return render(request, 'socio_update.html', context)


@login_required
@admin_required
def socio_delete(request, pk):
    """ Vista para eliminar un socio """
    socio = get_object_or_404(Socio, pk=pk)
    socio.delete(cascade=True)
    messages.success(request, 'Socio eliminado correctamente')
    return redirect('socio-listado')


@login_required
@admin_required
def socio_restore(request, pk):
    """ Restaurar un socio eliminado """
    socio = Socio.deleted_objects.get(pk=pk)
    socio.restore(cascade=True)
    messages.success(request, 'Socio restaurado correctamente')
    return redirect('socio-listado')


@login_required
@admin_required
def miembro_create_view(request, pk):
    """ Vista para crear un miembro """
    socio = get_object_or_404(Socio, pk=pk)
    if request.method == 'POST':
        persona = PersonaFormAdmin(request.POST, request.FILES)
        if persona.is_valid():
            miembro = persona.save(commit=False)
            miembro.socio = socio
            miembro.save()
            messages.success(request, 'Miembro creado correctamente')
            return redirect('socio-detalle', pk=socio.pk)
    else:
        miembro_form = MiembroForm()
    context = {
        'title': 'Crear miembro',
        'action': 'create',
        'miembro_form': miembro_form,
        'socio': socio,
    }
    return render(request, 'miembro_create.html', context)
