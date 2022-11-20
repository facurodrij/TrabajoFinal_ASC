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
from django.utils.translation import gettext_lazy as _
from django_softdelete.models import SoftDeleteModel

from core.models import Club


class User(AbstractUser, SoftDeleteModel):
    """
    Modelos de usuario personalizado.
    """
    username_validator = UnicodeUsernameValidator()
    persona = models.OneToOneField('accounts.Persona', on_delete=models.PROTECT, null=True, blank=True)
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

    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username

    def is_admin(self):
        """
        Devuelve true si el usuario es superusuario o staff del proyecto.
        """
        return self.is_superuser or self.is_staff

    def is_socio(self):
        """
        Devuelve true si el usuario es socio.
        """
        try:
            if self.persona is not None:
                return True if self.persona.get_socio() else False
            else:
                return False
        except ObjectDoesNotExist:
            return False

    def clean(self):
        super(User, self).clean()
        if not self.is_admin():
            if not self.persona:
                raise ValidationError('El usuario debe tener una persona asociada.')

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')


class PersonaAbstract(SoftDeleteModel):
    """
    Modelo abstracto de persona.
    Usado por Persona y SolicitudSocio.
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
        return self.get_full_name() + ' DNI: ' + self.dni

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
            # Si existe una imagen en self.imagen.url, la devuelve.
            Image.open(self.imagen.path)
            return self.imagen.url
        except FileNotFoundError:
            return settings.STATIC_URL + 'img/empty.svg'

    def get_fecha_nacimiento(self):
        """
        Devuelve la fecha de nacimiento de la persona.
        """
        return self.fecha_nacimiento.strftime('%Y/%m/%d')

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
        super(PersonaAbstract, self).clean()
        # Quitar espacios en blanco al principio y al final del nombre y apellido.
        self.nombre = self.nombre.strip()
        self.apellido = self.apellido.strip()

        # Cada palabra del nombre y apellido debe comenzar con mayúscula.
        self.nombre = self.nombre.title()
        self.apellido = self.apellido.title()

        # Fecha de nacimiento no puede ser mayor a la fecha actual.
        if self.fecha_nacimiento > datetime.now().date():
            raise ValidationError('Fecha de nacimiento: La fecha de nacimiento no puede ser mayor a la fecha actual.')

        # Si persona es socio_titular no puede ser menor a 16 años.
        try:
            if self.socio.es_titular() and self.get_edad() < 16:
                raise ValidationError('La persona debe ser mayor de 16 años.')
        except AttributeError:
            pass

    class Meta:
        abstract = True


class Persona(PersonaAbstract):
    """
    Modelo para almacenar los datos personales de los Usuarios
    """

    def get_socio(self, global_objects=False):
        """
        Devuelve el socio de la persona.
        """
        from socios.models import Socio
        if global_objects:
            try:
                return Socio.global_objects.get(persona=self)
            except ObjectDoesNotExist:
                return None
        try:
            return Socio.objects.get(persona=self)
        except ObjectDoesNotExist:
            return None

    def toJSON(self):
        """
        Devuelve un diccionario con los datos de la persona.
        """
        item = model_to_dict(self, exclude=['imagen'])
        item['imagen'] = self.get_imagen()
        item['edad'] = self.get_edad()
        item['fecha_nacimiento'] = self.get_fecha_nacimiento()
        item['socio'] = self.get_socio().__str__()
        item['__str__'] = self.__str__()
        return item

    def get_related_objects(self):
        """
        Devuelve una lista de objetos relacionados con la persona.
        """
        return [self.socio, self.user]

    class Meta:
        verbose_name = _('Persona')
        verbose_name_plural = _('Personas')
        constraints = [
            # Validar que el DNI solo contenga números, tenga al menos 7 dígitos y no comience con 0.
            models.CheckConstraint(check=models.Q(dni__regex=r'^[1-9][0-9]{6,}$'),
                                   name='persona_dni_valido',
                                   violation_error_message=_(
                                       'DNI: El DNI debe contener solo números, '
                                       'tener al menos 7 dígitos y no comenzar con 0.')),
            # Validar que el nombre y el apellido solo contengan letras y espacios.
            models.CheckConstraint(check=models.Q(nombre__regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$'),
                                   name='persona_nombre_valido',
                                   violation_error_message=_(
                                       'Nombre: El nombre solo puede contener letras y espacios.')),
            models.CheckConstraint(check=models.Q(apellido__regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$'),
                                   name='persona_apellido_valido',
                                   violation_error_message=_(
                                       'Apellido: El apellido solo puede contener letras y espacios.')),
        ]
