from PIL import Image
from django.conf import settings
from django.db import models
from django_softdelete.models import SoftDeleteModel


class Club(SoftDeleteModel):
    """
    Modelo del club.
    """
    localidad = models.ForeignKey('parameters.Localidad', on_delete=models.PROTECT)
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    direccion = models.CharField(max_length=255, verbose_name='Dirección')
    email = models.EmailField(max_length=255, verbose_name='Email')

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
