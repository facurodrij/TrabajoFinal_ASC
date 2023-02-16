from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.mail import EmailMessage
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.generic import ListView, DetailView, UpdateView, CreateView, DeleteView, FormView
from weasyprint import HTML, CSS

from accounts.decorators import admin_required
from accounts.forms import *
from core.models import Club, Persona
from socios.forms import SocioAdminForm, SocioParametersForm
from socios.models import Socio, Parameters


class SocioAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para listar los socios """
    model = Socio
    template_name = 'admin/socio/list.html'
    permission_required = 'socios.view_socio'
    context_object_name = 'socios'

    def get_queryset(self):
        return Socio.global_objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Socios'
        return context


class SocioAdminCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """ Vista para crear un socio """
    model = Socio
    form_class = SocioAdminForm
    template_name = 'admin/socio/form.html'
    permission_required = 'socio.add_socio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Socio'
        context['action'] = 'add'
        context['persona_id'] = self.request.GET.get('persona_id')
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        persona_id = self.request.GET.get('persona_id')
        # Si no existe la persona se inicializa el campo persona con filter(socio__isnull=True)
        if persona_id:
            # Si la persona existe pero ya tiene un socio se inicializa el campo persona con filter(socio__isnull=True)
            if Persona.objects.filter(pk=persona_id).exists():
                persona = Persona.objects.get(pk=persona_id)
                if persona.get_socio(global_objects=True):
                    form.fields['persona'].queryset = Persona.objects.filter(socio__isnull=True)
                else:
                    form.fields['persona'].queryset = Persona.objects.filter(pk=persona_id)
                    form.fields['persona'].initial = persona
        else:
            form.fields['persona'].queryset = Persona.objects.filter(socio__isnull=True)
        return form

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
                                mail_subject = 'Establecer contraseña.'
                                message = render_to_string(
                                    'registration/change_password_email.html', {
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
                                messages.success(self.request, 'Se ha creado un nuevo usuario con el email ingresado y '
                                                               'se ha enviado un email para establecer la contraseña.')
                        data = {'persona': socio.persona.toJSON(),
                                'socio': socio.toJSON(),
                                'swal_title': 'Socio creado',
                                'swal_text': 'El socio ha sido creado exitosamente.'}
                else:
                    data['error'] = form.errors
        except Exception as e:
            data['error'] = e.args[0]
        print('SocioAdminCreateView: ', data)
        return JsonResponse(data)


class SocioAdminDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Vista para mostrar un socio, solo para administradores
    """
    model = Socio
    template_name = 'admin/socio/detail.html'
    context_object_name = 'socio'
    permission_required = 'socios.view_socio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle de Socio'
        return context

    def get_object(self, queryset=None):
        return Socio.global_objects.get(pk=self.kwargs['pk'])


class SocioAdminUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para editar un socio, solo para administradores
    """
    model = Socio
    form_class = SocioAdminForm
    template_name = 'admin/socio/form.html'
    permission_required = 'socios.change_socio'
    context_object_name = 'socio'

    def get_object(self, queryset=None):
        return Socio.global_objects.get(pk=self.kwargs['pk'])

    def dispatch(self, request, *args, **kwargs):
        # Si el socio esta eliminado, redirigir a la vista de detalle de socio
        if self.get_object().is_deleted:
            return redirect('admin-socio-detalle', pk=self.get_object().pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Socio'
        context['action'] = 'edit'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['persona'].queryset = Persona.objects.filter(pk=self.get_object().persona.pk)
        form.fields['persona'].widget.attrs['hidden'] = True
        if self.get_object().get_user():
            form.fields['user'].initial = self.get_object().get_user().email
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
                        socio = form.save()
                        if not socio.get_user():
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
                                        messages.success(request, 'Al socio editado se lo ha vinculado con el'
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
                                    mail_subject = 'Establecer contraseña.'
                                    message = render_to_string(
                                        'registration/change_password_email.html', {
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
                                    messages.success(self.request,
                                                     'Se ha creado un nuevo usuario con el email ingresado'
                                                     ' y se ha enviado un email para establecer la contraseña.')
                        data = {'persona': self.get_object().persona.toJSON(),
                                'socio': self.get_object().toJSON(),
                                'swal_title': 'Socio editado',
                                'swal_text': 'El socio ha sido editado exitosamente.'}
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = e.args[0]
        print('SocioAdminUpdateView: ', data)
        return JsonResponse(data, safe=False)


class SocioAdminDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Vista para eliminar un socio, solo para administradores
    """
    model = Socio
    template_name = 'admin/socio/delete.html'
    permission_required = 'socios.delete_socio'
    context_object_name = 'socio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Baja de Socio'
        context['action'] = 'delete'
        context['miembros'] = self.object.get_miembros()
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            change_reason = request.POST['change_reason']
            if action == 'delete':
                # Si la acción es delete, se elimina únicamente al socio
                with transaction.atomic():
                    socio = self.get_object()
                    socio._change_reason = change_reason
                    socio.delete(cascade=False)
                    data['swal_title'] = 'Socio dado de baja'
                    data['swal_text'] = 'El socio ha sido dado de baja exitosamente.'
            elif action == 'delete_cascade':
                # Si la acción es delete_cascade, se elimina al socio y a todos sus miembros
                with transaction.atomic():
                    socio = self.get_object()
                    socio._change_reason = change_reason
                    socio.delete(cascade=True)
                    data['swal_title'] = 'Socio dado de baja'
                    data['swal_text'] = 'El socio y todos sus miembros han sido dados de baja exitosamente.'
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = e.args[0]
        print('SocioAdminDeleteView: ', data)
        return JsonResponse(data, safe=False)


class SocioAdminRestoreView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Vista para restaurar un socio, solo para administradores
    """
    permission_required = 'socios.restore_socio'

    def get_success_url(self):
        return reverse_lazy('admin-socio-detalle', kwargs={'pk': self.kwargs['pk']})

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            with transaction.atomic():
                socio = Socio.deleted_objects.get(pk=kwargs['pk'])
                socio.restore()
                messages.success(request, 'El socio ha sido restaurado exitosamente.')
            return redirect(self.get_success_url())
        except Exception as e:
            data['error'] = e.args[0]
        print('SocioAdminRestoreView: ', data)
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
        pass
    print('socio_admin_ajax: ', data)
    return JsonResponse(data, safe=False)


class ParametersSocioFormView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Vista para la edición de los parámetros de socios."""
    template_name = 'socios.html'
    form_class = SocioParametersForm
    permission_required = 'parameters.change_socios'
    success_url = reverse_lazy('admin-socio-parametros')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Parámetros de Socios'
        return context

    # Definir message success
    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Los parámetros de socios se guardaron correctamente.')
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Parameters.objects.get(club=Club.objects.get(pk=1))
        return kwargs
