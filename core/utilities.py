from django.conf import settings
from django.core.mail import EmailMessage
from django.template import loader


def send_email(subject, template, context, to, fail_silently=False):
    """
    Envía un correo electrónico con el asunto, plantilla, contexto y destinatario especificados.
    """
    message = loader.render_to_string(template, context)
    email = EmailMessage(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [to]
    )
    email.content_subtype = 'html'
    email.send(fail_silently=fail_silently)
