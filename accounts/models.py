from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, OperationalError
from django.forms import model_to_dict
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
    history = HistoricalRecords()

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
