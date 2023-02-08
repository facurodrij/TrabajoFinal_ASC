from datetime import datetime

from PIL import Image
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, OperationalError
from django.db.models.functions import Now
from django.forms import model_to_dict
from django.urls import reverse
from django_softdelete.models import SoftDeleteModel
from simple_history.models import HistoricalRecords

from socios.models import Socio, Parameters


class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Modelos de usuario personalizado.
    """
    email = models.EmailField(
        unique=True,
        verbose_name='Email',
        error_messages={
            "unique": "Un usuario con ese email ya existe.",
        },
    )
    username = None
    first_name = None
    last_name = None
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    apellido = models.CharField(max_length=255, verbose_name='Apellido')
    notificaciones = models.BooleanField(default=False, verbose_name='Notificaciones',
                                         help_text='Recibir notificaciones por email sobre eventos, '
                                                   'canchas liberadas, entre otros.')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    objects = CustomUserManager()

    def __str__(self):
        try:
            if self.is_admin():
                return self.socio.persona.get_full_name() + ' (Administrador)'
            return self.socio.persona.get_full_name()
        except AttributeError:
            if self.is_admin():
                return self.get_full_name() + ' (Administrador)'
            return self.get_full_name()
        except OperationalError:
            if self.is_admin():
                return self.get_full_name() + ' (Administrador)'
            return self.get_full_name()

    def get_full_name(self):
        return self.nombre + ' ' + self.apellido

    def get_short_name(self):
        return self.nombre

    def is_admin(self):
        """
        Devuelve true si el usuario es superusuario o staff del proyecto.
        """
        return self.is_superuser or self.is_staff

    def get_estado(self):
        """
        Devuelve el estado del usuario
        """
        return 'Activo' if self.is_active else 'Inactivo'

    def get_socio(self, global_object=False):
        """
        Devuelve el socio de la persona.
        """
        try:
            if global_object:
                return Socio.global_objects.get(user=self)
            return self.socio if not self.socio.is_deleted else None
        except ObjectDoesNotExist:
            return False

    def toJSON(self):
        item = model_to_dict(self)
        item['socio'] = self.get_socio().toJSON() if self.get_socio() else None
        return item

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'


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
        except FileNotFoundError:
            return settings.STATIC_URL + 'img/empty.svg'

    def get_fecha_nacimiento(self):
        """
        Devuelve la fecha de nacimiento de la persona.
        """
        return self.fecha_nacimiento.strftime('%Y-%m-%d')

    def es_titular(self):
        """
        Devuelve true si el campo persona_titular es nulo.
        """
        return True if self.persona_titular is None else False

    def get_personas_dependientes(self):
        """
        Devuelve una lista de personas dependientes de la persona.
        """
        return self.persona_set.all()

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

    def toJSON(self):
        """
        Devuelve un diccionario con los datos de la persona.
        """
        item = model_to_dict(self, exclude=['imagen', 'cuil'])
        item['imagen'] = self.get_imagen()
        item['cuil'] = self.cuil_completo
        item['edad'] = self.get_edad()
        item['fecha_nacimiento'] = self.get_fecha_nacimiento()
        item['socio'] = self.get_socio().__str__()
        item['url_editar'] = reverse('admin-persona-editar', kwargs={'pk': self.pk})
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
