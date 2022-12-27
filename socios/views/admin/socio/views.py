from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from weasyprint import HTML, CSS

from accounts.decorators import admin_required
from accounts.forms import *
from core.models import Club
from socios.forms import SocioAdminForm
from socios.models import Socio


class SocioAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para listar los socios """
    # TODO: Permitir filtrar por eliminados
    # TODO: Agregar todos los filtros
    model = Socio
    template_name = 'admin/socio/list.html'
    permission_required = 'socios.view_socio'
    context_object_name = 'socios'

    def get_queryset(self):
        return Socio.global_objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de socios'
        return context


class SocioAdminCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Socio
    form_class = SocioAdminForm
    template_name = 'admin/socio/form.html'
    permission_required = 'socio.add_socio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Socio'
        context['action'] = 'add'
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                form = self.form_class(request.POST, request.FILES)
                if form.is_valid():
                    with transaction.atomic():
                        socio = form.save()
                        email = request.POST['email']
                        if email:
                            try:
                                user = User.objects.get(email=email)
                                if user.get_socio(global_object=True):
                                    raise ValidationError('El email ingresado ya está en uso por el '
                                                          'socio {}.'.format(user.get_socio(global_object=True)))
                                else:
                                    socio.user = user
                                    socio.save()
                                    messages.success(request, 'Al socio creado se lo ha vinculado con el'
                                                              ' usuario {} existente.'.format(user))
                            except User.DoesNotExist:
                                user = User.objects.create_user(email=email,
                                                                password=User.objects.make_random_password(),
                                                                nombre=socio.persona.nombre,
                                                                apellido=socio.persona.apellido,
                                                                is_active=True)
                                socio.user = user
                                socio.save()
                                # Enviar email para cambiar la contraseña
                                current_site = get_current_site(self.request)
                                mail_subject = 'Activación de cuenta.'
                                message = render_to_string('email/change_password.html', {
                                    'user': user,
                                    'domain': current_site.domain,
                                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                                    'token': PasswordResetTokenGenerator().make_token(user),
                                    'protocol': 'https' if self.request.is_secure() else 'http',
                                    'club': Club.objects.first(),
                                })
                                to_email = user.email
                                email = EmailMessage(
                                    mail_subject, message, to=[to_email]
                                )
                                email.send()
                                messages.success(self.request, 'Se ha enviado un email para establecer la contraseña.')
                        data = {'persona': socio.persona.toJSON(), 'socio': socio.toJSON()}
                else:
                    data['error'] = form.errors
        except Exception as e:
            data['error'] = e.args[0]
        print(data)
        return JsonResponse(data)


class SocioAdminDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Vista para mostrar un socio, solo para administradores
    TODO: Si esta eliminado, mostrar un mensaje de que esta eliminado y mostrar el botón de restaurar
    TODO: Agregar todos los filtros
    """
    model = Socio
    template_name = 'admin/socio/detail.html'
    context_object_name = 'socio'
    permission_required = 'socios.view_socio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle de Socio'
        context['grupo_familiar'] = self.object.grupo_familiar()
        return context

    def get_object(self, queryset=None):
        return Socio.global_objects.get(pk=self.kwargs['pk'])


class SocioAdminUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para editar un socio, solo para administradores
    TODO: Actualizar vista de actualizar socio
    TODO: Si el socio esta eliminado, redirigir a la vista de detalle de socio
    """
    model = Socio
    form_class = SocioAdminForm
    template_name = 'admin/socio/form.html'
    permission_required = 'socios.change_socio'
    context_object_name = 'socio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Socio'
        context['action'] = 'edit'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['persona'].queryset = Persona.objects.filter(pk=self.get_object().persona.pk)
        form.fields['persona'].widget.attrs['disabled'] = True
        form.fields['email'].initial = self.get_object().get_user().email
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                # Si la acción es editar, se edita el socio
                form = self.form_class(request.POST, instance=self.get_object())
                if form.is_valid():
                    with transaction.atomic():
                        form.save()
                        messages.success(request, 'Socio actualizado correctamente')
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = e.args[0]
        print(data)
        return JsonResponse(data, safe=False)


@login_required
@admin_required
def socio_history_pdf(request, socio_pk, history_pk):
    socio = Socio.global_objects.get(pk=socio_pk)
    club = Club.objects.get(pk=1)
    history = socio.history.get(pk=history_pk)
    html_string = render_to_string('admin/socio/history_pdf.html', {'history': history,
                                                                    'socio': socio,
                                                                    'club': club})
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    html.write_pdf(target='/tmp/socio_historial.pdf',
                   stylesheets=[CSS('{}/libs/bootstrap-4.6.2/bootstrap.min.css'.format(settings.STATICFILES_DIRS[0]))])
    fs = FileSystemStorage('/tmp')
    with fs.open('socio_historial.pdf') as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="socio_historial.pdf"'
        return response


@login_required
@admin_required
def socio_admin_ajax(request):
    data = {}
    # Obtener si el GET o POST
    if request.method == 'GET':
        action = request.GET['action']
        if action == 'get_persona':
            # Si la acción es get_persona, se obtiene la persona
            try:
                try:
                    persona = Persona.global_objects.get(dni=request.GET['dni'])
                except KeyError:
                    persona = Persona.global_objects.get(pk=request.GET['id'])
                if persona.is_deleted:
                    data = {'persona_is_deleted': persona.toJSON()}
                elif persona.get_socio(global_objects=True):
                    data = {'persona_is_socio': persona.toJSON(),
                            'socio': persona.get_socio(global_objects=True).toJSON()}
                else:
                    data = {'persona': persona.toJSON()}
            except Persona.DoesNotExist:
                pass
    elif request.method == 'POST':
        action = request.POST['action']
        if action == 'add_persona':
            # Si la acción es add_persona, se crea una nueva persona
            form = PersonaAdminForm(request.POST, request.FILES)
            if form.is_valid():
                with transaction.atomic():
                    persona = form.save(commit=False)
                    persona.club = Club.objects.get(pk=1)
                    persona.save()
                    data = {'persona': persona.toJSON()}
            else:
                data['error'] = form.errors
    print('socio_admin_ajax: ', data)
    return JsonResponse(data, safe=False)
