from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.conf import settings


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    """Atributo OneToOneField para relacionar el modelo Profile con el modelo User."""

    bio = models.TextField(max_length=500, null=True, blank=True)
    """Atributo para almacenar la biografía del usuario."""

    def avatar_directory_path(self, filename):
        """Funcion para guardar el archivo en MEDIA_ROOT/user_<id>/<filename>"""
        return 'profile_avatars/user_{0}/{1}'.format(self.user.id, filename)

    avatar = models.ImageField(upload_to=avatar_directory_path, null=True, blank=True)
    """Atributo para almacenar la imagen de perfil del usuario."""

    def __str__(self):
        """Metodo para representar el objeto Profile."""
        return self.user.username

    def save(self, *args, **kwargs):
        """Metodo save() sobrescrito para redimensionar la imagen."""
        if self.avatar:
            img = Image.open(self.avatar.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.avatar.path)
        super().save(*args, **kwargs)

    def get_avatar(self):
        """Metodo para obtener la imagen de perfil del usuario."""
        if self.avatar:
            return self.avatar.url
        else:
            return settings.STATIC_URL + 'img/empty.png'
