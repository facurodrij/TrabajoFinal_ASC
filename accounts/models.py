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
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("Username: Una persona con ese nombre de usuario ya existe."),
            "invalid": _(
                "Username: Este campo solo puede contener letras, números y los siguientes caracteres: @/./+/-/_"),
        },
    )
    email = models.EmailField(
        unique=True,
        verbose_name=_('Email'),
        error_messages={
            "unique": _("Email: Una persona con ese email ya existe."),
        },
    )
    first_name = None
    last_name = None

    def __str__(self):
        return self.username

    def get_full_name(self):
        """
        Devuelve el nombre completo del usuario.
        """
        return self.usuariopersona.persona.get_full_name()

    def get_short_name(self):
        """
        Devuelve el nombre corto del usuario.
        """
        return self.usuariopersona.persona.get_short_name()

    def get_edad(self):
        """
        Devuelve la edad del usuario.
        """
        return self.usuariopersona.persona.get_edad()

    def get_imagen(self):
        """
        Devuelve la imagen del usuario.
        """
        return self.usuariopersona.persona.get_imagen()

    def is_admin(self):
        """
        Devuelve true si el usuario es superusuario o staff del proyecto.
        """
        return self.is_superuser or self.is_staff

    def is_admin_club(self):
        """
        Devuelve true si el usuario es administrador del club.
        """
        return self.user_permissions.get(codename='change_club')

    def is_socio(self):
        """
        Devuelve true si el usuario es socio del club.
        """
        try:
            if self.socioindividual:
                return True
        except ObjectDoesNotExist:
            return False

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')


class Persona(SoftDeleteModel):
    """
    Modelo para almacenar los datos personales de los Usuarios
    o Miembros No Registrados de un Grupo Familiar.
    """
    dni = models.CharField(max_length=9, unique=True, verbose_name=_('DNI'),
                           error_messages={
                               "unique": _("DNI: Una persona con ese DNI ya existe."),
                           })
    sexo = models.ForeignKey('parameters.Sexo', on_delete=models.PROTECT, verbose_name=_('Sexo'))
    nombre = models.CharField(max_length=255, verbose_name=_('Nombre'))
    apellido = models.CharField(max_length=255, verbose_name=_('Apellido'))
    fecha_nacimiento = models.DateField(verbose_name=_('Fecha de nacimiento'),
                                        error_messages={
                                            "invalid": _("Fecha de nacimiento: Formato de fecha inválido."),
                                        },
                                        )
    localidad = models.ForeignKey('parameters.Localidad', on_delete=models.PROTECT, verbose_name=_('Localidad'))
    direccion = models.CharField(max_length=255, verbose_name=_('Dirección'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

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
        if self.imagen:
            return self.imagen.url
        else:
            return settings.STATIC_URL + 'img/empty.svg'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.imagen:
            img = Image.open(self.imagen.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.imagen.path)

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

        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9 ]+$', self.direccion):
            raise ValidationError(_('Dirección: La dirección solo puede contener letras, números y espacios.'))

        # Quitar espacios en blanco al principio y al final del nombre, apellido y dirección
        self.nombre = self.nombre.strip()
        self.apellido = self.apellido.strip()
        self.direccion = self.direccion.strip()

        return super(Persona, self).clean()

    class Meta:
        verbose_name = _('Persona')
        verbose_name_plural = _('Personas')


class UsuarioPersona(SoftDeleteModel):
    """
    Modelo para relacionar usuario y persona. Este modelo es necesario
    porque el modelo Miembro No Registrado no tiene Usuario, pero si se
    relaciona con Persona.
    """
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    """Atributo OneToOneField para relacionar el modelo UsuarioPersona con el modelo User."""
    persona = models.OneToOneField(Persona, on_delete=models.PROTECT)
    """Atributo OneToOneField para relacionar el modelo UsuarioPersona con el modelo Persona."""

    def __str__(self):
        return 'Usuario: ' + self.user.__str__() + ' - Persona: ' + self.persona.__str__()

    class Meta:
        unique_together = ('user', 'persona')
