from PIL import Image
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
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
