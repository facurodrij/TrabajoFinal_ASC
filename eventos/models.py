from datetime import datetime, timedelta

from PIL import Image
from django.conf import settings
from django.db import models
from django.forms import model_to_dict
from django_softdelete.models import SoftDeleteModel


class Parameters(models.Model):
    club = models.OneToOneField('core.Club', on_delete=models.PROTECT, verbose_name='Club',
                                related_name='evento_parameters')
    minutos_expiracion_venta = models.PositiveSmallIntegerField(default=5,
                                                                verbose_name='Minutos de expiración por falta de pago',
                                                                help_text=
                                                                'La venta de tickets debe ser pagada dentro de esta cantidad de'
                                                                ' minutos, de lo contrario se cancelará.')

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


class Ticket(SoftDeleteModel):
    """
    Modelo de los tickets.
    """
    venta_ticket = models.ForeignKey('eventos.VentaTicket', on_delete=models.PROTECT, verbose_name='Venta')
    ticket_variante = models.ForeignKey('eventos.TicketVariante', on_delete=models.PROTECT,
                                        verbose_name='Variante de ticket')
    nombre = models.CharField(max_length=255, verbose_name='Nombre del cliente')
    is_used = models.BooleanField(default=False, verbose_name='Usado')
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')

    def __str__(self):
        return self.pk

    def toJSON(self):
        item = model_to_dict(self)
        item['venta_ticket'] = self.venta_ticket.toJSON()
        item['ticket_variante'] = self.ticket_variante.toJSON()
        return item

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = "Tickets"


class VentaTicket(SoftDeleteModel):
    """
    Modelo de las ventas de tickets.
    """
    email = models.EmailField(verbose_name='Email')
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total')
    pagado = models.BooleanField(default=False, verbose_name='Pagado', help_text='Marcar si el cliente ya pagó')
    preference_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='Preference ID',
                                     help_text='ID de la preferencia de pago de Mercado Pago')
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')

    def __str__(self):
        return self.pk

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

    def __str__(self):
        return self.pk

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

    def __str__(self):
        return self.pk

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
