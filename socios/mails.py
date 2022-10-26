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


def send_email(request, socio, mail_subject, template):
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
