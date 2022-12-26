from django.contrib.auth import (
    logout, get_user_model)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.sites.shortcuts import get_current_site
from django.core.files.storage import FileSystemStorage
from django.core.mail import EmailMessage
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.generic import FormView, UpdateView, CreateView, ListView
from weasyprint import HTML

from accounts.decorators import *
from accounts.forms import *
from accounts.tokens import account_activation_token
from parameters.models import ClubParameters

User = get_user_model()


class SignUpView(FormView):
    """
    Vista para que un usuario se registre en el sistema.
    """
    template_name = 'registration/signup.html'
    form_class = SignUpForm
    success_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return super(SignUpView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(SignUpView, self).get_context_data(**kwargs)
        context['title'] = 'Registro'
        return context

    def form_valid(self, form):
        # Enviar un Email de activación de cuenta
        with transaction.atomic():
            user = form.save()
            current_site = get_current_site(self.request)
            mail_subject = 'Active su cuenta.'
            message = render_to_string('email/activate_account.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
                'protocol': 'https' if self.request.is_secure() else 'http',
                'club': Club.objects.first(),
            })
            to_email = user.email
            email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            email.send()
        messages.success(self.request, 'Se ha enviado un email a su casilla para que active su cuenta.')
        return redirect('login')


class CustomLoginView(LoginView):
    form_class = LoginForm
    sucess_url = reverse_lazy('index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login'
        return context

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)
            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True
        return super().form_valid(form)


@login_required
def persona_view(request):
    """
    Vista para ver los datos personales del usuario.
    """
    context = {
        'title': 'Datos Personales',
    }
    return render(request, 'persona_detail.html', context)


def activate_account(request, uidb64, token):
    """
    Vista para activar la cuenta de usuario.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Gracias por activar su cuenta. Ahora puede ingresar al sistema.')
        return redirect('login')
    else:
        messages.error(request, 'El link de activación es inválido.')
        return redirect('login')


class PersonaAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para el listado de personas """
    # TODO: Permitir filtrar por eliminados
    model = Persona
    template_name = 'admin/persona/list.html'
    permission_required = 'accounts.view_persona'
    context_object_name = 'personas'

    def get_queryset(self):
        return Persona.global_objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Personas'
        return context


class PersonaAdminCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """ Vista para la creación de personas """
    # TODO: Generar comprobante de operación
    model = Persona
    form_class = PersonaAdminForm
    template_name = 'admin/persona/form.html'
    permission_required = 'accounts.add_persona'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva Persona'
        context['action'] = 'add'
        return context

    # Si en la url existe 'titular=true', se deshabilita el campo es_menor del formulario
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.GET.get('titular'):
            form.fields['es_menor'].widget.attrs['disabled'] = True
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                form = self.form_class(request.POST, request.FILES)
                if form.is_valid():
                    with transaction.atomic():
                        persona = form.save()
                        persona_titular = form.cleaned_data.get('persona_titular')
                        if persona_titular:
                            persona.persona_titular = persona_titular
                            persona.save()
                            persona.validate()
                            persona.persona_titular.validate()
                        else:
                            persona.validate()
                        data['persona'] = persona.toJSON()
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = e.args[0]
        print(data)
        return JsonResponse(data)


class PersonaAdminUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """ Vista para la actualización de personas """
    # TODO: Generar comprobante de operación
    # TODO: Si la persona esta eliminada, redirigir a su detalle
    model = Persona
    form_class = PersonaAdminForm
    template_name = 'admin/persona/form.html'
    permission_required = 'accounts.change_persona'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar persona'
        context['action'] = 'edit'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['persona_titular'].initial = self.object.persona_titular
        form.fields['persona_titular'].queryset = Persona.objects.filter(persona_titular__isnull=True).exclude(
            pk=self.object.pk)
        if self.object.persona_set.exists():
            form.fields['persona_titular'].widget.attrs['disabled'] = True
            form.fields['persona_titular'].help_text = 'No se puede modificar porque la persona tiene personas a cargo.'
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                form = self.form_class(request.POST, request.FILES, instance=self.get_object())
                if form.is_valid():
                    with transaction.atomic():
                        persona_titular = form.cleaned_data.get('persona_titular')
                        if persona_titular:
                            persona = form.save(commit=False)
                            persona.persona_titular = persona_titular
                            persona.save()
                            persona.validate()
                        else:
                            persona = form.save(commit=False)
                            persona.persona_titular = None
                            persona.save()
                            persona.validate()
                        messages.success(request, 'Persona actualizada correctamente.')
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = e.args[0]
        print(data)
        return JsonResponse(data)


@login_required
@admin_required
def persona_history_pdf(request):
    """ Vista para generar el pdf de la historia de una persona """
    if request.method == 'GET':
        action = request.GET['action']
        if action == 'print':
            try:
                persona_id = request.GET['persona_id']
                persona = Persona.global_objects.get(pk=persona_id)
                html_string = render_to_string('admin/persona/comprobante.html', {'persona': persona})
                html = HTML(string=html_string, base_url=request.build_absolute_uri())
                html.write_pdf(target='/tmp/personas.pdf')
                fs = FileSystemStorage('/tmp')
                with fs.open('personas.pdf') as pdf:
                    response = HttpResponse(pdf, content_type='application/pdf')
                    response['Content-Disposition'] = 'inline; filename="personas.pdf"'
                    return response
            except Exception as e:
                print(e.args[0])
                return HttpResponse('Error al generar el PDF')

# TODO: PersonaAdminDetailView
# TODO: PersonaAdminDeleteView
