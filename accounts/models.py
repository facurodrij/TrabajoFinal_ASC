import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import UnicodeUsernameValidator
from django_softdelete.models import SoftDeleteModel
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
        return self.usuariopersona.persona.nombre + ' ' + self.usuariopersona.persona.apellido

    def get_short_name(self):
        """
        Devuelve el nombre corto del usuario.
        """
        return self.usuariopersona.persona.nombre

    def get_imagen(self):
        """
        Devuelve la imagen del usuario.
        """
        if self.usuariopersona.persona.imagen:
            return self.usuariopersona.persona.imagen.url
        else:
            return settings.STATIC_URL + 'img/empty.svg'

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
        return 'img/{0}/{1}/{2}'.format(self._meta.model_name, self.usuariopersona.user.username, filename)

    imagen = models.ImageField(upload_to=image_directory_path, null=True, blank=True, verbose_name=_('Imagen'))

    def __str__(self):
        return self.dni

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.imagen:
            img = Image.open(self.imagen.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.imagen.path)

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
