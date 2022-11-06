from django.views.generic import (
    CreateView, UpdateView, DeleteView, ListView, DetailView,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from django.contrib.auth.views import LoginView
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import (
    REDIRECT_FIELD_NAME, get_user_model, login as auth_login,
    logout as auth_logout, update_session_auth_hash,
)
from django.utils.safestring import mark_safe
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMessage

from .forms import *
from .decorators import *

User = get_user_model()


@no_login_required
def signup(request):
    """
    Vista para que un socio sin usuario pueda registrarse.
    Para que un socio pueda registrarse con esta vista deben estar sus datos en la
    tabla Persona y esos datos deben estar asociados con la tabla Socio.
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        # Obtener DNI y Email
        try:
            dni = form.clean_dni()
            email = form.clean_email()
        except forms.ValidationError as e:
            messages.error(request, e.message)
            return redirect('signup')
        # Obtener la Persona con el DNI ingresado
        persona = Persona.objects.get(dni=dni)

        # Crear el Usuario con el Email ingresado y Username igual al DNI ingresado
        user = User.objects.create_user(username=dni,
                                        email=email,
                                        persona=persona,
                                        password=User.objects.make_random_password())

        # Enviar un Email al Usuario con un enlace para cambiar su contraseña
        current_site = get_current_site(request)
        mail_subject = 'Active su cuenta.'
        message = render_to_string('email/activate_account.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': PasswordResetTokenGenerator().make_token(user),
            'protocol': 'https' if request.is_secure() else 'http',
        })
        to_email = email
        email = EmailMessage(
            mail_subject, message, to=[to_email]
        )
        email.send()
        messages.success(request, 'Se ha enviado un email a su casilla para que active su cuenta.')
        return redirect('login')
    else:
        form = SignUpForm()
    context = {
        'title': 'Registro',
        'form': form,
    }
    return render(request, 'registration/signup.html', context)


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
        return super(CustomLoginView, self).form_valid(form)
        # TODO: Validar que el usuario no esté asociado a Persona que:
        # 1. No esté asociada a Socio
        # 2. Esté asociada a Socio pero que esté eliminado
        # 3. No esté asociada a Personal
        # 4. Esté asociada a Personal pero que esté eliminado
        # Aclaración: Si el usuario es admin no se debe validar nada.


@login_required
def persona_view(request):
    """
    Vista para ver los datos personales del usuario.
    """
    context = {
        'title': 'Datos Personales',
    }
    return render(request, 'persona_detail.html', context)
