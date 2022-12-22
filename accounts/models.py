from datetime import datetime

from PIL import Image
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UnicodeUsernameValidator
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import model_to_dict
from django.urls import reverse
from django_softdelete.models import SoftDeleteModel
from simple_history.models import HistoricalRecords

from core.models import Club
from socios.models import Socio


class User(AbstractUser, SoftDeleteModel):
    """
    Modelos de usuario personalizado.
    """
    username_validator = UnicodeUsernameValidator()
    socio = models.OneToOneField('socios.Socio', on_delete=models.PROTECT, null=True, blank=True)
    email = models.EmailField(
        unique=True,
        verbose_name='Email',
        error_messages={
            "unique": "Email: Una persona con ese email ya existe.",
        },
    )
    username = models.CharField(
        "Nombre de usuario",
        max_length=150,
        unique=True,
        help_text="Requerido. 150 caracteres o menos. Letras, dígitos y @/./+/-/_ solamente.",
        validators=[username_validator],
        error_messages={
            "unique": "Nombre de usuario: Una persona con ese nombre de usuario ya existe.",
            "invalid":
                "Nombre de usuario: Este campo solo puede contener letras, números y los "
                "siguientes caracteres: @/./+/-/_",
        },
    )
    first_name = None
    last_name = None

    REQUIRED_FIELDS = ['email']

    def __str__(self):
        try:
            if self.is_admin():
                return self.socio.persona.get_full_name() + ' (Administrador)'
            return self.socio.persona.get_full_name()
        except AttributeError:
            return self.username

    def is_admin(self):
        """
        Devuelve true si el usuario es superusuario o staff del proyecto.
        """
        return self.is_superuser or self.is_staff

    def get_socio(self, global_object=False):
        """
        Devuelve el socio de la persona.
        """
        try:
            if global_object:
                return Socio.global_objects.get(persona=self.socio.persona)
            return self.socio
        except ObjectDoesNotExist:
            return False

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'


class Persona(SoftDeleteModel):
    """
    Modelo para almacenar los datos personales de los Usuarios
    """
    cuil = models.CharField(max_length=11, unique=True, verbose_name='CUIL',
                            error_messages={'unique': 'CUIL: Una persona con ese CUIL ya existe.'})
    sexo = models.ForeignKey('parameters.Sexo', on_delete=models.PROTECT, verbose_name='Sexo')
    club = models.ForeignKey('core.Club', on_delete=models.PROTECT, verbose_name='Club')
    persona_titular = models.ForeignKey(
        'self', on_delete=models.PROTECT, verbose_name='Persona titular', null=True, blank=True)
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    apellido = models.CharField(max_length=255, verbose_name='Apellido')
    fecha_nacimiento = models.DateField(verbose_name='Fecha de nacimiento',
                                        error_messages={
                                            "invalid": "Fecha de nacimiento: Formato de fecha inválido.",
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
        return self.get_full_name() + ' (' + self.cuil + ')'

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
        except FileNotFoundError:
            return settings.STATIC_URL + 'img/empty.svg'

    def get_fecha_nacimiento(self):
        """
        Devuelve la fecha de nacimiento de la persona.
        """
        return self.fecha_nacimiento.strftime('%d/%m/%Y')

    def es_titular(self):
        """
        Devuelve true si el campo persona_titular es nulo.
        """
        return self.persona_titular is None

    def get_socio(self, global_objects=False):
        """
        Devuelve el socio de la persona.
        """
        try:
            if global_objects:
                return Socio.global_objects.get(persona=self)
            return self.socio
        except ObjectDoesNotExist:
            return None

    def get_related_objects(self):
        """
        Devuelve una lista de objetos relacionados con la persona.
        """
        return [self.socio]

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

    def toJSON(self):
        """
        Devuelve un diccionario con los datos de la persona.
        """
        item = model_to_dict(self, exclude=['imagen'])
        item['imagen'] = self.get_imagen()
        item['edad'] = self.get_edad()
        item['fecha_nacimiento'] = self.get_fecha_nacimiento()
        item['socio'] = self.get_socio().__str__()
        item['url_editar'] = reverse('admin-persona-editar', kwargs={'pk': self.pk})
        item['__str__'] = self.__str__()
        return item

    def clean(self):
        super(Persona, self).clean()
        if not self.es_titular():
            if not self.persona_titular.es_titular():
                raise ValidationError('Persona titular: La persona seleccionada no es titular.')
            # Si la persona no es titular, no puede tener personas a su cargo.
            if self.persona_set.exists():
                raise ValidationError('La persona actual no puede tener personas a su cargo.')

        # Quitar espacios en blanco al principio y al final del nombre y apellido.
        self.nombre = self.nombre.strip()
        self.apellido = self.apellido.strip()

        # Cada palabra del nombre y apellido debe comenzar con mayúscula.
        self.nombre = self.nombre.title()
        self.apellido = self.apellido.title()

        # Fecha de nacimiento no puede ser mayor a la fecha actual.
        if self.fecha_nacimiento > datetime.now().date():
            raise ValidationError('Fecha de nacimiento: La fecha de nacimiento no puede ser mayor a la fecha actual.')

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
        ]
