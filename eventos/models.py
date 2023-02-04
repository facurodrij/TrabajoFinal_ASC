import base64
from datetime import datetime, timedelta
from io import BytesIO

import qrcode
from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import models, transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django_softdelete.models import SoftDeleteModel
from num2words import num2words
from qrcode.image.svg import SvgPathFillImage


class Parameters(models.Model):
    club = models.OneToOneField('core.Club', on_delete=models.PROTECT, verbose_name='Club',
                                related_name='evento_parameters')
    minutos_expiracion_venta = models.PositiveSmallIntegerField(default=5,
                                                                verbose_name='Minutos de expiración por falta de pago',
                                                                help_text=
                                                                'La venta de tickets debe ser pagada dentro de esta'
                                                                ' cantidad de minutos, de lo contrario se cancelará.')
    max_tickets_por_venta = models.PositiveSmallIntegerField(default=10,
                                                             verbose_name='Máximo de tickets por venta',
                                                             help_text='Máximo cantidad de tickets que se pueden '
                                                                       'comprar en una sola venta.')

    class Meta:
        verbose_name = 'Parámetro de evento'
        verbose_name_plural = "Parámetros de eventos"


class Evento(SoftDeleteModel):
    """
    Modelo de los eventos.
    """
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    descripcion = models.TextField(verbose_name='Descripción')
    fecha_inicio = models.DateField(verbose_name='Fecha de inicio')
    hora_inicio = models.TimeField(verbose_name='Hora de inicio')
    fecha_fin = models.DateField(verbose_name='Fecha de finalización')
    hora_fin = models.TimeField(verbose_name='Hora de finalización')
    registro_deadline = models.DateField(verbose_name='Fecha límite de registro', null=True, blank=True,
                                         help_text='Fecha límite para registrarse al evento. Si no se especifica, '
                                                   'no hay límite.')
    mayor_edad = models.BooleanField(verbose_name='Mayor de edad', default=False,
                                     help_text='Indica si el evento es para mayores de edad.')
    is_active = models.BooleanField(verbose_name='Activo', default=True)
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')

    def image_directory_path(self, filename):
        """
        Devuelve la ruta de la imagen de perfil del usuario.
        """
        return 'img/{0}/{1}/{2}'.format(self._meta.model_name, datetime.now().strftime('%Y-%m-%d'), filename)

    imagen = models.ImageField(upload_to=image_directory_path, verbose_name='Imagen')

    def __str__(self):
        return self.nombre

    def get_imagen(self):
        """
        Devuelve la imagen de la persona.
        """
        try:
            # Si existe una imagen en self.imagen.url, la devuelve.
            Image.open(self.imagen.path)
            return self.imagen.url
        except FileNotFoundError:
            return settings.STATIC_URL + 'img/empty.svg'

    def get_expiration_date(self, isoformat=True):
        """
        Devuelve la fecha de expiración del evento.
        """
        if isoformat:
            return self.registro_deadline.isoformat() if self.registro_deadline else self.fecha_inicio.isoformat()
        return self.registro_deadline if self.registro_deadline else self.fecha_inicio

    def get_start_datetime(self):
        """
        Devuelve la fecha y hora de inicio del evento.
        """
        return datetime.combine(self.fecha_inicio, self.hora_inicio)

    def get_end_datetime(self):
        """
        Devuelve la fecha y hora de finalización del evento.
        """
        return datetime.combine(self.fecha_fin, self.hora_fin)

    def save(self, *args, **kwargs):
        """Método save() sobrescrito para redimensionar la imagen."""
        super().save(*args, **kwargs)
        try:
            img = Image.open(self.imagen.path)
            if img.height > 2000 or img.width > 2000:
                output_size = (2000, 2000)
                img.thumbnail(output_size)
                img.save(self.imagen.path)
        except FileNotFoundError:
            pass

    def toJSON(self):
        """
        Devuelve el objeto en formato JSON.
        """
        item = model_to_dict(self, exclude=['imagen'])
        item['imagen'] = self.get_imagen()
        return item

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = "Eventos"
        constraints = [
            models.CheckConstraint(
                check=models.Q(fecha_inicio__lte=models.F('fecha_fin')),
                name='fecha_inicio_menor_fecha_fin',
                violation_error_message='La fecha de inicio debe ser menor o igual a la fecha de finalización.'
            )
        ]


class TicketVariante(SoftDeleteModel):
    """
    Modelo de las variantes de los tickets.
    """
    evento = models.ForeignKey('Evento', on_delete=models.PROTECT, verbose_name='Evento')
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio')
    total_tickets = models.PositiveIntegerField(verbose_name='Total de tickets')
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')

    def __str__(self):
        return '{} - ${}'.format(self.nombre, self.precio)

    def get_tickets_restantes(self):
        """
        Devuelve la cantidad de tickets restantes.
        """
        return self.total_tickets - self.ticket_set.filter(is_deleted=False).count()

    def toJSON(self):
        """
        Devuelve el objeto en formato JSON.
        """
        item = model_to_dict(self, exclude=['precio'])
        item['evento'] = self.evento.toJSON()
        item['precio'] = self.precio.__str__()
        return item

    class Meta:
        verbose_name = 'Variante de ticket'
        verbose_name_plural = "Variantes de tickets"


def send_qr_code(ids, email=None):
    """
    Envía el código QR de cada ticket al correo del cliente. Solo se envía un correo al cliente.
    """
    tickets = Ticket.objects.filter(pk__in=ids)
    if len(tickets) > 0:
        # Obtener los correos de los tickets.
        if not email:
            emails = [ticket.venta_ticket.user.email for ticket in tickets]
        else:
            emails = [email]
        # Adjuntar los códigos QR de los tickets como archivos.
        attachments = []
        for ticket in tickets:
            qr_code = ticket.get_qr_code(format_png=True)
            attachments.append(('qr_{}_{}.png'.format('ticket', ticket.pk), qr_code, 'image/png'))
        message = render_to_string('email/qr.html', {
            'tickets': tickets,
        })
        email = EmailMessage(
            'Códigos QR de los tickets',
            message,
            settings.DEFAULT_FROM_EMAIL,
            emails,
        )
        email.content_subtype = 'html'
        email.attachments = attachments
        email.send()


class Ticket(SoftDeleteModel):
    """
    Modelo de los tickets.
    """
    venta_ticket = models.ForeignKey('eventos.VentaTicket', on_delete=models.PROTECT, verbose_name='Venta')
    ticket_variante = models.ForeignKey('eventos.TicketVariante', on_delete=models.PROTECT,
                                        verbose_name='Variante de ticket')
    nombre = models.CharField(max_length=255, verbose_name='Nombre del cliente')
    is_used = models.BooleanField(default=False, verbose_name='Usado')
    check_date = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de check-in')
    check_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, null=True, blank=True,
                                 verbose_name='Escaneado por')
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')

    def get_qr_code(self, format_png=False):
        """
        Devuelve el código QR del ticket.
        """
        factory = SvgPathFillImage
        url = reverse('admin-tickets-qr', kwargs={'pk': self.pk})
        qr_string = "http://127.0.0.1:8000" + url
        img = qrcode.make(qr_string, image_factory=factory, box_size=20, border=1)
        stream = BytesIO()
        img.save(stream)
        base64_data = base64.b64encode(stream.getvalue()).decode()
        # Pasar a formato PNG para adjuntar en el correo.
        if format_png:
            return base64.b64decode(base64_data)
        return 'data:image/svg+xml;utf8;base64,' + base64_data

    def get_precio_compra(self):
        """
        Devuelve el precio de compra del ticket.
        """
        cantidad = self.venta_ticket.itemventaticket_set.get(ticket_variante=self.ticket_variante).cantidad
        subtotal = self.venta_ticket.itemventaticket_set.get(ticket_variante=self.ticket_variante).subtotal
        return subtotal / cantidad

    def get_estado_pago(self):
        """
        Devuelve el estado del pago del ticket.
        """
        if self.venta_ticket.pagoventaticket.status == 'approved':
            return 'Aprobado'
        return 'Pendiente'

    def toJSON(self):
        item = model_to_dict(self)
        item['venta_ticket'] = self.venta_ticket.toJSON()
        item['ticket_variante'] = self.ticket_variante.toJSON()
        return item

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = "Tickets"
        constraints = [
            models.CheckConstraint(
                check=~Q(is_used=True) | Q(check_date__isnull=False),
                name='ticket_check_date_not_null_if_is_used_is_true',
                violation_error_message='El campo "Fecha de check-in" no puede ser nulo si el ticket está usado.'
            ),
            models.CheckConstraint(
                check=~Q(is_used=True) | Q(check_by__isnull=False),
                name='ticket_check_by_not_null_if_is_used_is_true',
                violation_error_message='El campo "Escaneado por" no puede ser nulo si el ticket está usado.'
            ),
        ]


class VentaTicket(SoftDeleteModel):
    """
    Modelo de las ventas de tickets.
    """
    evento = models.ForeignKey('eventos.Evento', on_delete=models.PROTECT, verbose_name='Evento')
    email = models.EmailField(verbose_name='Correo electrónico')
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total')
    pagado = models.BooleanField(default=False, verbose_name='Pagado', help_text='Marcar si el cliente ya pagó')
    preference_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='Preference ID',
                                     help_text='ID de la preferencia de pago de Mercado Pago')
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')

    def get_expiration_date(self, isoformat=True):
        """
        Devuelve la fecha de expiración de la venta.
        """
        minutos = Parameters.objects.get(club_id=1).minutos_expiracion_venta
        return (self.date_created + timedelta(minutes=minutos)).isoformat() if isoformat else \
            self.date_created + timedelta(minutes=minutos)

    def get_related_objects(self):
        """
        Devuelve los objetos relacionados con la venta.
        """
        return self.ticket_set.all()

    def get_TOTAL_letras(self):
        """
        Devuelve el total de la venta en letras.
        """
        return 'Son: {} pesos argentinos'.format(num2words(self.total, lang='es'))

    def clean(self):
        """Método clean() sobrescrito para validar la reserva."""
        super(VentaTicket, self).clean()
        # Si pasó la fecha de expiración de la reserva y no se ha pagado, se cancela.
        if self.date_created:
            if self.get_expiration_date(isoformat=False) < timezone.now() and not self.pagado:
                print('La venta de ticket #{} ha expirado por falta de pago.'.format(self.id))
                with transaction.atomic():
                    self.delete(cascade=True)
                raise ValidationError('La venta de ticket #{} ha expirado por falta de pago.'.format(self.id),
                                      code='invalid', params={'id': self.id})

    def toJSON(self):
        """
        Devuelve el modelo en formato JSON.
        """
        item = model_to_dict(self, exclude=['total'])
        item['total'] = self.total.__str__()
        return item

    class Meta:
        verbose_name = 'Venta de ticket'
        verbose_name_plural = "Ventas de tickets"


class ItemVentaTicket(models.Model):
    """
    Modelo de los detalles de las ventas de tickets.
    """
    venta_ticket = models.ForeignKey('eventos.VentaTicket', on_delete=models.PROTECT, verbose_name='Venta')
    ticket_variante = models.ForeignKey('eventos.TicketVariante', on_delete=models.PROTECT,
                                        verbose_name='Variantes de ticket')
    cantidad = models.PositiveIntegerField(verbose_name='Cantidad')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Subtotal')

    def get_precio_unit(self):
        """
        Devuelve el precio unitario del item.
        """
        return self.subtotal / self.cantidad

    def toJSON(self):
        """
        Devuelve el modelo en formato JSON.
        """
        item = model_to_dict(self, exclude=['subtotal'])
        item['subtotal'] = self.subtotal.__str__()
        return item

    class Meta:
        verbose_name = 'Item de venta de ticket'
        verbose_name_plural = "Items de ventas de tickets"


class PagoVentaTicket(models.Model):
    """
    Modelo de los pagos de las ventas de tickets.
    """
    venta_ticket = models.OneToOneField('eventos.VentaTicket', on_delete=models.PROTECT, verbose_name='Venta de ticket')
    payment_id = models.CharField(max_length=255, verbose_name='Payment ID')
    status = models.CharField(max_length=50, verbose_name='Estado')
    status_detail = models.CharField(max_length=255, verbose_name='Detalle del estado')
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto de la transacción')
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')
    date_approved = models.DateTimeField(verbose_name='Fecha de aprobación')

    def toJSON(self):
        """
        Devuelve el modelo en formato JSON.
        """
        item = model_to_dict(self)
        item['venta_ticket'] = self.venta_ticket.toJSON()
        return item

    class Meta:
        verbose_name = 'Pago de venta de ticket'
        verbose_name_plural = "Pagos de ventas de tickets"
