from django.shortcuts import render, redirect
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
from django.core.mail import EmailMessage

from .models import UsuarioPersona
from .forms import *
from .decorators import *
from .tokens import account_activation_token
from socios.decorators import socio_required

User = get_user_model()


def send_activation_email(request, user):
    current_site = get_current_site(request)
    mail_subject = 'Activa tu cuenta.'
    message = render_to_string('email/activate.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http',
    })
    to_email = user.email
    email = EmailMessage(
        mail_subject, message, to=[to_email]
    )
    email.send()


@no_login_required
def signup(request):
    """ Vista para el registro de un usuario """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Guardar el usuario en memoria, no en la base de datos
            user = form.save(commit=False)
            # Establecer el usuario como no activo
            user.is_active = False
            # Guardar el usuario en la base de datos
            user.save()
            # Enviar el correo de activación
            send_activation_email(request, user)
            messages.success(request, 'Se ha enviado un correo de activación a tu cuenta de correo.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    context = {
        'title': 'Registro',
        'form': form,
    }
    return render(request, 'registration/signup.html', context)


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()

        messages.success(request, 'Gracias por activar tu cuenta. Ahora puedes iniciar sesión.')
        return redirect('login')
    else:
        messages.error(request, 'El enlace de activación es inválido.')

    return redirect('login')


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
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
        """Security check complete. Log the user in."""
        auth_login(self.request, form.get_user())
        if not self.request.user.is_admin():
            # Si inicia sesión un socio con estado inactivo, se le redirige al login
            if self.request.user.is_socio() and not self.request.user.socio.estado.is_active:
                messages.error(self.request,
                               'Tu estado de socio no está activo. ' + self.request.user.socio.estado.descripcion)
                auth_logout(self.request)
                return redirect('login')
        return super(CustomLoginView, self).form_valid(form)


@login_required
@socio_required
@permission_required('accounts.change_persona', raise_exception=True)
def persona_detail_view(request):
    """
    Vista para ver los datos personales del usuario.
    """
    try:
        persona = request.user.usuariopersona.persona
    except ObjectDoesNotExist:
        persona = None
    context = {
        'title': 'Datos personales',
        'persona': persona,
    }
    return render(request, 'persona_detail.html', context)
