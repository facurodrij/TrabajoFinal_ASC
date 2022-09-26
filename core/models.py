from django.db import models
from django_softdelete.models import SoftDeleteModel, SoftDeleteManager


class Club(SoftDeleteModel):
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    pais = models.ForeignKey('parameters.Pais', on_delete=models.PROTECT, verbose_name='País')
    provincia = models.ForeignKey('parameters.Provincia', on_delete=models.PROTECT)
    localidad = models.ForeignKey('parameters.Localidad', on_delete=models.PROTECT)
    direccion = models.CharField(max_length=255, verbose_name='Dirección')
    socios = models.ManyToManyField('accounts.User', through='Socio', related_name='socios')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def logo_directory_path(self, filename):
        """Metodo para obtener la ruta de la imagen del logo del club."""
        return 'img/club_logo/{0}/{1}'.format(self.id, filename)

    logo = models.ImageField(upload_to=logo_directory_path, verbose_name='Logo')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Club'
        verbose_name_plural = "Clubes"


class Socio(models.Model):
    id = models.BigAutoField(primary_key=True)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    categoria = models.ForeignKey('parameters.SocioCategoria', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

    class Meta:
        unique_together = ('club', 'user')
        verbose_name = 'Socio'
        verbose_name_plural = "Socios"


class Cancha(models.Model):
    numero = models.SmallIntegerField(verbose_name='Número')
    deporte = models.ForeignKey('parameters.Deporte', on_delete=models.PROTECT)
    capacidad = models.SmallIntegerField(verbose_name='Capacidad por equipo')
    superficie = models.ForeignKey('parameters.Superficie', on_delete=models.PROTECT)
    techado = models.BooleanField(default=False, verbose_name='¿Es techada?')
    iluminacion = models.BooleanField(default=False, verbose_name='Iluminación')
    precio = models.DecimalField(max_digits=20, decimal_places=2, verbose_name='Precio por hora')
    club = models.ForeignKey(Club, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'Cancha {0} - {1}'.format(self.numero, self.club.nombre)

    class Meta:
        unique_together = ('numero', 'club', 'deporte')
        verbose_name = 'Cancha'
        verbose_name_plural = "Canchas"
