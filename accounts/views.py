from django.contrib.auth import (
    logout, get_user_model, login)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.generic import FormView, UpdateView, CreateView, ListView

from core.models import Club
from .decorators import *
from .forms import *
from .tokens import account_activation_token

User = get_user_model()


class SignUpView(FormView):
    """
    Vista para que un socio sin usuario pueda registrarse.
    Para que un socio pueda registrarse con esta vista deben estar sus datos en la
    tabla Persona y esos datos deben estar asociados con la tabla Socio.
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
        # Obtener DNI, Email y SocioID
        dni = form.clean_dni()
        email = form.clean_email()
        socio_id = form.clean_socio_id()
        # Obtener la Persona con el DNI ingresado
        persona = Persona.objects.get(dni=dni)
        # Crear el Usuario con el Email ingresado y Username igual al DNI ingresado
        with transaction.atomic():
            user = User(username=dni,
                        email=email,
                        persona=persona)
            user.set_password(form.cleaned_data['password1'])
            user.is_active = False
            user.save()
        # Enviar un Email de activación de cuenta
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
        to_email = email
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
        # User validate after login
        user = form.get_user()
        login(self.request, user)
        if not user.is_admin():
            if user.persona.get_socio(global_objects=True) is None:
                messages.error(self.request, 'Su cuenta no está asociada a un socio de la institución.')
                return redirect('logout')
            if user.persona.get_socio(global_objects=True).is_deleted:
                messages.error(self.request, 'Su cuenta de socio ha sido dada de baja.')
                # TODO: Agregar motivo de la baja
                return redirect('logout')
            return redirect('persona')
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
    model = Persona
    template_name = 'admin/persona/list.html'
    permission_required = 'accounts.view_persona'
    context_object_name = 'personas'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Personas'
        return context


class PersonaAdminCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """ Vista para la creación de personas """
    model = Persona
    form_class = PersonaFormAdmin
    template_name = 'admin/persona/form.html'
    permission_required = 'accounts.add_persona'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva persona'
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
                        persona = form.save(commit=False)
                        persona.club = Club.objects.first()
                        persona.save()
                        messages.success(request, 'Persona creada correctamente.')
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        print(data)
        return JsonResponse(data)


class PersonaAdminUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """ Vista para la actualización de personas """
    model = Persona
    form_class = PersonaFormAdmin
    template_name = 'admin/persona/form.html'
    permission_required = 'accounts.change_persona'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar persona'
        context['action'] = 'edit'
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                form = self.form_class(request.POST, request.FILES, instance=self.get_object())
                if form.is_valid():
                    with transaction.atomic():
                        form.save()
                        messages.success(request, 'Persona creada correctamente.')
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        print(data)
        return JsonResponse(data)
