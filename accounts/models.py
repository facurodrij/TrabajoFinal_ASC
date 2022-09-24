import uuid
import os.path as path
from django.db import models
from django.contrib.auth.models import AbstractUser
from PIL import Image
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django import template
from django.template.defaultfilters import register
from django.contrib.auth.models import UnicodeUsernameValidator


class User(AbstractUser):
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

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    """Atributo OneToOneField para relacionar el modelo Profile con el modelo User."""

    bio = models.TextField(max_length=500, null=True, blank=True, verbose_name=_('Biografía'))
    genero = models.ForeignKey('parameters.Genero', blank=True, on_delete=models.CASCADE, verbose_name=_('Género'))

    def avatar_directory_path(self, filename):
        """Funcion para guardar el archivo en MEDIA_ROOT/user_<id>/<filename>"""
        return 'profile_avatars/user_{0}/{1}'.format(self.user.id, filename)

    avatar = models.ImageField(upload_to=avatar_directory_path, null=True, blank=True, verbose_name=_('Avatar'))
    """Atributo para almacenar la imagen de perfil del usuario."""

    def __str__(self):
        """Metodo para representar el objeto Profile."""
        return self.user.username

    # Redimensionar la imagen de perfil
    def save(self, *args, **kwargs):
        """Metodo save() sobrescrito para redimensionar la imagen."""
        super().save(*args, **kwargs)
        try:
            img = Image.open(self.avatar.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.avatar.path)
        except Exception as e:
            print(e)

    def get_avatar(self):
        """Metodo para obtener la imagen de perfil del usuario."""
        if self.avatar:
            return self.avatar.url
        else:
            return settings.STATIC_URL + 'img/empty.png'

    class Meta:
        verbose_name = _('Perfil')
        verbose_name_plural = _('Perfiles')
