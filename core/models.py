from datetime import timedelta, datetime

from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
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
    is_pagado = models.BooleanField(default=False, verbose_name='Pagado')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    asistido = models.BooleanField(default=False, verbose_name='Asistido')

    def __str__(self):
        return 'Reserva #{}'.format(self.id)

    def get_fecha(self):
        """
        Devuelve la fecha de nacimiento de la persona.
        """
        return self.fecha.strftime('%Y-%m-%d')

    def start(self):
        """Método para obtener la fecha y hora de inicio de la reserva."""
        return datetime.combine(self.fecha, self.hora).isoformat()

    def end(self):
        """Método para obtener la fecha y hora de fin de la reserva."""
        return (datetime.combine(self.fecha, self.hora) + timedelta(hours=1)).isoformat()

    def color(self):
        """Método para obtener el color de la reserva."""
        if datetime.combine(self.fecha, self.hora) + timedelta(hours=1) < datetime.now():
            return '#8496a9'
        else:
            return '#0275d8'

    # TODO: Crear en el modelo User un método para obtener las reservas realizadas a partir del email.

    def clean(self):
        """Método clean() sobrescrito para validar la reserva."""
        super(Reserva, self).clean()
        # Si pasaron 10 minutos desde la creación de la reserva y no se ha pagado, se cancela.
        if self.created_at:
            if self.created_at + timedelta(minutes=10) < timezone.now() and not self.is_pagado:
                self.delete()
                raise ValidationError('La reserva ha expirado.')

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
    TODO: Agregar los campos que trae el modelo de Pago de MercadoPago.
    """
    reserva = models.OneToOneField('Reserva', on_delete=models.PROTECT, verbose_name='Reserva')
    fecha = models.DateField(auto_now_add=True, verbose_name='Fecha')
    monto = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Monto')

    def __str__(self):
        return 'Pago de reserva #{}'.format(self.reserva.id)

    class Meta:
        verbose_name = 'Pago de reserva'
        verbose_name_plural = "Pagos de reservas"
