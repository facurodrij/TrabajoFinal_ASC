from datetime import datetime

from PIL import Image
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import models
from django.db.models.functions import Now
from django.forms import model_to_dict
from django_softdelete.models import SoftDeleteModel
from simple_history.models import HistoricalRecords

from accounts.models import User
from socios.models import Socio


class Club(SoftDeleteModel):
    """
    Modelo del club.
    """
    localidad = models.ForeignKey('parameters.Localidad', on_delete=models.PROTECT)
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    direccion = models.CharField(max_length=255, verbose_name='Dirección')
    email = models.EmailField(max_length=255, verbose_name='Email')
    history = HistoricalRecords()

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


class Persona(SoftDeleteModel):
    """
    Modelo para almacenar los datos personales de los Usuarios
    """
    cuil = models.CharField(max_length=11, unique=True, verbose_name='CUIL',
                            error_messages={'unique': 'Una persona con ese CUIL ya existe.'})
    sexo = models.ForeignKey('parameters.Sexo', on_delete=models.PROTECT, verbose_name='Sexo')
    club = models.ForeignKey('core.Club', on_delete=models.PROTECT, verbose_name='Club')
    persona_titular = models.ForeignKey(
        'self', on_delete=models.PROTECT, verbose_name='Persona titular', null=True, blank=True)
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    apellido = models.CharField(max_length=255, verbose_name='Apellido')
    fecha_nacimiento = models.DateField(verbose_name='Fecha de nacimiento',
                                        error_messages={
                                            "invalid": "Formato de fecha de nacimiento inválido.",
                                        })
    history = HistoricalRecords()

    @property
    def cuil_completo(self):
        """
        Devuelve el CUIL completo de la persona.
        """
        return self.cuil[:2] + '-' + self.cuil[2:10] + '-' + self.cuil[10:]

    def image_directory_path(self, filename):
        """
        Devuelve la ruta de la imagen de perfil del usuario.
        """
        return 'img/{0}/{1}/{2}'.format(self._meta.model_name, self.cuil, filename)

    imagen = models.ImageField(upload_to=image_directory_path, verbose_name='Foto carnet')

    def __str__(self):
        return self.get_full_name() + ' (' + self.cuil_completo + ')'

    def get_full_name(self):
        """
        Devuelve el nombre completo de la persona.
        """
        return self.nombre + ' ' + self.apellido

    def get_edad(self):
        edad = relativedelta(datetime.now(), self.fecha_nacimiento)
        return edad.years

    def get_imagen(self):
        """
        Devuelve la imagen de la persona.
        """
        try:
            # Si existe una imagen en self.imagen.url, la devuelve.
            Image.open(self.imagen.path)
            return self.imagen.url
        except (FileNotFoundError, ValueError):
            return settings.STATIC_URL + 'img/empty.svg'

    def es_titular(self):
        """
        Devuelve true si el campo persona_titular es nulo.
        """
        return True if self.persona_titular is None else False

    def get_socio(self, global_objects=False):
        """
        Devuelve el socio de la persona. Si existe y está activo.
        """
        try:
            if global_objects:
                return Socio.global_objects.get(persona=self)
            return self.socio if self.socio.is_deleted is False else None
        except Socio.DoesNotExist:
            return None

    def grupo_familiar(self):
        """
        Devuelve el grupo familiar de la persona.
        """
        if self.es_titular():
            return self.persona_set.all()
        else:
            return self.persona_titular.persona_set.all()


    def get_related_objects(self):
        """
        Devuelve una lista de objetos relacionados con la persona.
        """
        return [self.socio]

    def toJSON(self):
        """
        Devuelve un diccionario con los datos de la persona.
        """
        item = model_to_dict(self, exclude=['imagen', 'cuil'])
        item['imagen'] = self.get_imagen()
        item['cuil'] = self.cuil_completo
        item['edad'] = self.get_edad()
        item['fecha_nacimiento'] = self.fecha_nacimiento.strftime('%d/%m/%Y')
        item['socio'] = self.get_socio().__str__()
        item['__str__'] = self.__str__()
        return item

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

    def clean(self):
        super(Persona, self).clean()

        # Quitar espacios en blanco al principio y al final del nombre y apellido.
        self.nombre = self.nombre.strip()
        self.apellido = self.apellido.strip()

        # Cada palabra del nombre y apellido debe comenzar con mayúscula.
        self.nombre = self.nombre.title()
        self.apellido = self.apellido.title()

    class Meta:
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'
        constraints = [
            # Validar que el CUIL Argentino sea válido.
            models.CheckConstraint(check=models.Q(cuil__regex=r'^[0-9]{11}$'),
                                   name='cuil_valido',
                                   violation_error_message='CUIL: Formato de CUIL inválido.'),
            # Validar que persona_titular no sea self.
            models.CheckConstraint(
                check=models.Q(persona_titular__isnull=True) | ~models.Q(persona_titular_id=models.F('id')),
                name='persona_titular_distinta',
                violation_error_message='Persona titular: La persona titular no puede ser la misma persona.'),
            # Validar que el nombre y el apellido solo contengan letras y espacios.
            models.CheckConstraint(check=models.Q(nombre__regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$'),
                                   name='persona_nombre_valido',
                                   violation_error_message='Nombre: El nombre solo puede contener letras y espacios.'),
            models.CheckConstraint(check=models.Q(apellido__regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$'),
                                   name='persona_apellido_valido',
                                   violation_error_message='Apellido: El apellido solo puede contener letras y'
                                                           ' espacios.'),
            # Validar la fecha de nacimiento.
            models.CheckConstraint(check=models.Q(fecha_nacimiento__lte=Now()),
                                   name='persona_fecha_nacimiento_valida',
                                   violation_error_message='Fecha de nacimiento: La fecha de nacimiento no puede'
                                                           ' ser mayor a la fecha actual.'),
        ]
