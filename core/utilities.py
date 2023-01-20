from smtplib import SMTPException

from django.core.mail import EmailMessage
from django.template import loader


def send_email(subject, template, context, to):
    """
    Envía un correo electrónico con el asunto, plantilla, contexto y destinatario especificados.
    """
    try:
        message = loader.render_to_string(template, context)
        email = EmailMessage(subject, message, to=to)
        email.content_subtype = 'html'
        email.send()
    except SMTPException as e:
        print('Ha ocurrido un error al enviar el correo electrónico: ', e)
