from datetime import timedelta, datetime

import pytz
from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django_softdelete.models import SoftDeleteModel


class Club(SoftDeleteModel):
    """
    Modelo del club.
    """
    localidad = models.ForeignKey('parameters.Localidad', on_delete=models.PROTECT)
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    direccion = models.CharField(max_length=255, verbose_name='Dirección')
    email = models.EmailField(max_length=255, verbose_name='Email')

    def imagen_directory_path(self, filename):
        """Método para obtener la ruta de la imagen del logo del club."""
        return 'img/club/{0}/{1}'.format(self.id, filename)

    imagen = models.ImageField(upload_to=imagen_directory_path, null=True, blank=True, verbose_name='Logo')

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        """Método save() sobrescrito para redimensionar la imagen."""
        super().save(*args, **kwargs)
        try:
            img = Image.open(self.imagen.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.imagen.path)
        except FileNotFoundError:
            pass

    def get_imagen(self):
        """Método para obtener la imagen de perfil del usuario."""
        try:
            # Si existe una imagen en self.imagen.url, la devuelve.
            Image.open(self.imagen.path)
            return self.imagen.url
        except FileNotFoundError:
            return settings.STATIC_URL + 'img/empty.svg'

    class Meta:
        unique_together = ('localidad', 'direccion')
        verbose_name = 'Club'
        verbose_name_plural = "Clubes"
        ordering = ['id']


class Cancha(SoftDeleteModel):
    """
    Modelo de la cancha.
    """
    club = models.ForeignKey(Club, on_delete=models.PROTECT)
    superficie = models.ForeignKey('parameters.Superficie', on_delete=models.PROTECT)
    deporte = models.ForeignKey('parameters.Deporte', on_delete=models.PROTECT)
    hora_laboral = models.ManyToManyField('HoraLaboral',
                                          through='CanchaHoraLaboral',
                                          through_fields=('cancha', 'hora_laboral'))
    cantidad_jugadores = models.PositiveSmallIntegerField(default=5,
                                                          verbose_name='Cantidad de jugadores',
                                                          help_text='Cantidad de jugadores por equipo',
                                                          validators=[MinValueValidator(4), MaxValueValidator(11)],
                                                          null=True, blank=True)
    precio = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Precio por hora')
    precio_luz = models.DecimalField(max_digits=6,
                                     decimal_places=2,
                                     null=True, blank=True,
                                     verbose_name='Precio por hora con luz')

    def imagen_directory_path(self, filename):
        """Método para obtener la ruta de la imagen de la cancha."""
        return 'img/cancha/{0}/{1}'.format(self.id, filename)

    imagen = models.ImageField(upload_to=imagen_directory_path, null=True, blank=True, verbose_name='Imagen')

    def __str__(self):
        return 'Cancha #{}'.format(self.id)

    def save(self, *args, **kwargs):
        """Método save() sobrescrito para redimensionar la imagen."""
        super().save(*args, **kwargs)

        try:
            img = Image.open(self.imagen.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.imagen.path)
        except (FileNotFoundError, ValueError):
            pass

    def get_imagen(self):
        """Método para obtener la imagen de perfil del usuario."""
        try:
            # Si existe una imagen en self.imagen.url, la devuelve.
            Image.open(self.imagen.path)
            return self.imagen.url
        except FileNotFoundError:
            return settings.STATIC_URL + 'img/empty.svg'

    class Meta:
        verbose_name = 'Cancha'
        verbose_name_plural = "Canchas"
        ordering = ['id']
        constraints = [
            # El precio por hora con luz no puede ser menor al precio por hora.
            models.CheckConstraint(check=models.Q(precio_luz__gte=models.F('precio')),
                                   name='precio_luz_mayor_precio',
                                   violation_error_message='El precio por hora con luz no '
                                                           'puede ser menor al precio por hora.')
        ]


class CanchaHoraLaboral(models.Model):
    """
    Modelo del horario de la cancha.
    """
    cancha = models.ForeignKey('Cancha', on_delete=models.PROTECT)
    hora_laboral = models.ForeignKey('HoraLaboral', on_delete=models.PROTECT)
    con_luz = models.BooleanField(default=False, verbose_name='Con luz')

    def __str__(self):
        return 'Cancha #{} - {}'.format(self.cancha.id, self.hora_laboral)

    class Meta:
        unique_together = ('cancha', 'hora_laboral')
        verbose_name = 'Horario de cancha'
        verbose_name_plural = "Horarios de canchas"


class HoraLaboral(models.Model):
    """
    Modelo de la hora laboral.
    """
    club = models.ForeignKey(Club, on_delete=models.PROTECT)
    hora = models.TimeField(verbose_name='Hora')

    def __str__(self):
        return str(self.hora)

    class Meta:
        unique_together = ('club', 'hora')
        verbose_name = 'Hora laboral'
        verbose_name_plural = "Horas laborales"
        ordering = ['hora']


class Reserva(SoftDeleteModel):
    """
    Modelo de la reserva.
    """
    cancha = models.ForeignKey('Cancha', on_delete=models.PROTECT)
    nombre = models.CharField(max_length=50, verbose_name='Nombre (cliente)')
    email = models.EmailField(verbose_name='Email (cliente)')
    fecha = models.DateField(verbose_name='Fecha')
    hora = models.TimeField(verbose_name='Hora')
    con_luz = models.BooleanField(default=False, verbose_name='Con luz')
    nota = models.TextField(null=True, blank=True, verbose_name='Nota')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    asistido = models.BooleanField(default=False, verbose_name='Asistido')
    expira = models.BooleanField(default=False, verbose_name='Expira (falta de pago)')
    FORMA_PAGO = (
        (1, 'Presencial'),
        (2, 'Online'),
    )
    forma_pago = models.PositiveSmallIntegerField(choices=FORMA_PAGO, default=1, verbose_name='Forma de pago')
    preference_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='Preference ID',
                                     help_text='ID de la preferencia de pago de Mercado Pago')

    def __str__(self):
        return 'Reserva #{}'.format(self.id)

    def is_paid(self):
        """Método para saber si la reserva está pagada."""
        if self.forma_pago == 1:
            return True
        if self.forma_pago == 2:
            try:
                if self.pagoreserva.status == 'approved':
                    return True
                else:
                    return False
            except (PagoReserva.DoesNotExist, AttributeError):
                return False

    def is_finished(self):
        """Método para saber si la reserva ya finalizó."""
        return self.end_datetime() < datetime.now().isoformat()

    def start_date(self):
        """
        Devuelve la fecha de la reserva en formato yyyy-mm-dd.
        """
        return self.fecha.strftime('%Y-%m-%d')

    def start_datetime(self):
        """Método para obtener la fecha y hora de inicio de la reserva."""
        return datetime.combine(self.fecha, self.hora).isoformat()

    def end_datetime(self):
        """Método para obtener la fecha y hora de fin de la reserva."""
        return (datetime.combine(self.fecha, self.hora) + timedelta(hours=1)).isoformat()

    def color(self):
        """Método para obtener el color de la reserva."""
        if datetime.combine(self.fecha, self.hora) + timedelta(hours=1) < datetime.now():
            return '#8496a9'
        else:
            return '#0275d8'

    def get_FORMA_PAGO_display(self):
        """Método para obtener el nombre de la forma de pago."""
        return dict(self.FORMA_PAGO)[self.forma_pago]

    def get_price(self):
        """Método para obtener el precio de la reserva."""
        if self.con_luz:
            return self.cancha.precio_luz
        return self.cancha.precio

    def get_expiration_date(self):
        """Método para obtener la fecha de expiración de la reserva, en caso de que la forma de pago sea online."""
        # TODO: Hacer que la reserva expire solamente si no es creada por el administrador.
        if self.expira:
            # TODO: Parametrizar la cantidad de minutos para que expire la reserva.
            return self.created_at + timedelta(minutes=20)
        return None

    # TODO: Crear en el modelo User un método para obtener las reservas realizadas a partir del email.

    def clean(self):
        """Método clean() sobrescrito para validar la reserva."""
        super(Reserva, self).clean()
        # Si pasó la fecha de expiración de la reserva y no se ha pagado, se cancela.
        if self.created_at:
            if self.get_expiration_date() < datetime.now() and not self.is_paid():
                self.delete()
                raise ValidationError('La reserva {} ha expirado.'.format(self.id))

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = "Reservas"
        constraints = [
            # Validar que no exista una reserva con la misma cancha, fecha, hora y is_deleted=False,
            # pero si con is_deleted=True.
            models.UniqueConstraint(fields=['cancha', 'fecha', 'hora'],
                                    condition=models.Q(is_deleted=False),
                                    name='reserva_unico')
        ]


class PagoReserva(models.Model):
    """
    Modelo del pago de la seña de la reserva.
    """
    payment_id = models.CharField(max_length=255, verbose_name='ID de pago')
    reserva = models.OneToOneField('Reserva', on_delete=models.CASCADE)
    preference_id = models.CharField(max_length=255, verbose_name='ID de preferencia')
    date_created = models.DateTimeField(verbose_name='Fecha de creación')
    date_approved = models.DateTimeField(verbose_name='Fecha de aprobación')
    date_last_updated = models.DateTimeField(verbose_name='Fecha de última actualización')
    payment_method_id = models.CharField(max_length=50, verbose_name='Método de pago')
    payment_type_id = models.CharField(max_length=50, verbose_name='Tipo de pago')
    status = models.CharField(max_length=50, verbose_name='Estado')
    status_detail = models.CharField(max_length=255, verbose_name='Detalle del estado')
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto de la transacción')

    def __str__(self):
        return 'Pago de reserva #{}'.format(self.reserva.id)

    class Meta:
        verbose_name = 'Pago de reserva'
        verbose_name_plural = "Pagos de reservas"
