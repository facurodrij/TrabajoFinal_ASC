import re
import uuid
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import UnicodeUsernameValidator
from django_softdelete.models import SoftDeleteModel
from django.core.exceptions import ValidationError
from PIL import Image


class User(AbstractUser, SoftDeleteModel):
    """
    Modelos de usuario personalizado.
    """
    username_validator = UnicodeUsernameValidator()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    persona = models.OneToOneField('accounts.Persona', on_delete=models.PROTECT)
    email = models.EmailField(
        unique=True,
        verbose_name=_('Email'),
        error_messages={
            "unique": _("Email: Una persona con ese email ya existe."),
        },
    )
    username = models.CharField(
        _("Nombre de usuario"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("Nombre de usuario: Una persona con ese nombre de usuario ya existe."),
            "invalid": _(
                "Nombre de usuario: Este campo solo puede contener letras, números y los siguientes caracteres: @/./+/-/_"),
        },
    )
    first_name = None
    last_name = None

    def __str__(self):
        return self.username

    def is_admin(self):
        """
        Devuelve true si el usuario es superusuario o staff del proyecto.
        """
        return self.is_superuser or self.is_staff

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')


class Persona(SoftDeleteModel):
    """
    Modelo para almacenar los datos personales de los Usuarios
    o Miembros No Registrados de un Grupo Familiar.
    """
    dni = models.CharField(max_length=8, unique=True, verbose_name=_('DNI'),
                           error_messages={
                               "unique": _("DNI: Una persona con ese DNI ya existe."),
                           })
    sexo = models.ForeignKey('parameters.Sexo', on_delete=models.PROTECT, verbose_name=_('Sexo'))
    club = models.ForeignKey('core.Club', on_delete=models.PROTECT, verbose_name=_('Club'))
    nombre = models.CharField(max_length=255, verbose_name=_('Nombre'))
    apellido = models.CharField(max_length=255, verbose_name=_('Apellido'))
    fecha_nacimiento = models.DateField(verbose_name=_('Fecha de nacimiento'),
                                        error_messages={
                                            "invalid": _("Fecha de nacimiento: Formato de fecha inválido."),
                                        })

    def image_directory_path(self, filename):
        """
        Devuelve la ruta de la imagen de perfil del usuario.
        """
        return 'img/{0}/{1}/{2}'.format(self._meta.model_name, self.dni, filename)

    imagen = models.ImageField(upload_to=image_directory_path, verbose_name=_('Imagen'))

    def __str__(self):
        return self.dni

    def get_full_name(self):
        """
        Devuelve el nombre completo de la persona.
        """
        return self.nombre + ' ' + self.apellido

    def get_short_name(self):
        """
        Devuelve el nombre corto de la persona.
        """
        return self.nombre

    def get_edad(self):
        edad = relativedelta(datetime.now(), self.fecha_nacimiento)
        return edad.years

    def get_imagen(self):
        """
        Devuelve la imagen de la persona.
        """
        try:
            return self.imagen.url
        except Exception as e:
            print(e)
            return settings.STATIC_URL + 'img/empty.svg'

    def get_socio(self):
        """
        Devuelve el socio de la persona.
        """
        try:
            return self.socio
        except ObjectDoesNotExist:
            return None

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
        # Validar que el DNI sea correcto
        if not self.dni.isdigit():
            raise ValidationError(_('DNI: El DNI debe contener solo números.'))
        if not len(self.dni) >= 7:
            raise ValidationError(_('DNI: El DNI debe contener al menos 7 dígitos.'))
        if self.dni[0] == '0':
            raise ValidationError(_('DNI: El DNI no puede comenzar con 0.'))

        # El nombre y el apellido pueden contener letras y espacios
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$', self.nombre):
            raise ValidationError(_('Nombre: El nombre solo puede contener letras y espacios.'))
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$', self.apellido):
            raise ValidationError(_('Apellido: El apellido solo puede contener letras y espacios.'))

        # Quitar espacios en blanco al principio y al final del nombre y apellido.
        self.nombre = self.nombre.strip()
        self.apellido = self.apellido.strip()

        return super(Persona, self).clean()

    class Meta:
        verbose_name = _('Persona')
        verbose_name_plural = _('Personas')
