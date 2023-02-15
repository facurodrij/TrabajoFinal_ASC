from django.contrib.auth import (
    logout, get_user_model)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.generic import FormView, UpdateView

from accounts.decorators import *
from accounts.forms import *
from accounts.tokens import account_activation_token
from core.models import Club

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
            message = render_to_string('registration/activate_account_email.html', {
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
    success_url = reverse_lazy('index')

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


class ProfileUserView(LoginRequiredMixin, UpdateView):
    """ Vista para el perfil de usuario """
    model = User
    template_name = 'user/profile.html'
    form_class = ProfileForm
    success_url = reverse_lazy('user-perfil')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Perfil de Usuario'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        context['socio'] = self.object.get_socio() if self.object.get_socio() else None
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Usuario actualizado correctamente.')
        return super().form_valid(form)


class ChangeEmailView(LoginRequiredMixin, UpdateView):
    """ Vista para cambiar el email de usuario """
    model = User
    template_name = 'user/change_email.html'
    form_class = ChangeEmailForm
    success_url = reverse_lazy('user-perfil')

    def get_object(self, queryset=None):
        return self.request.user

    def get_initial(self):
        return {'email': ''}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cambiar Email'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context

    def form_valid(self, form):
        with transaction.atomic():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            current_site = get_current_site(self.request)
            mail_subject = 'Active su cuenta.'
            message = render_to_string('registration/activate_account_email.html', {
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
