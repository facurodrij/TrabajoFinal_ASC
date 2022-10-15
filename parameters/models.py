from django.db import models
from django.utils.translation import gettext_lazy as _


# PARÁMETROS DEL SISTEMA
# Parámetros para perfiles de usuario
class Sexo(models.Model):
    """Modelo para almacenar los sexos de los usuarios."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name=_('Nombre'))

    class Meta:
        verbose_name = _('Sexo')
        verbose_name_plural = _('Sexos')

    def __str__(self):
        return self.nombre


# Parámetros para las canchas
class Deporte(models.Model):
    """Modelo para almacenar los deportes."""
    nombre = models.CharField(max_length=255, verbose_name=_('Nombre'))
    cant_jugadores = models.SmallIntegerField(null=True, blank=True, verbose_name=_('Cantidad de jugadores por equipo'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Deporte')
        verbose_name_plural = _('Deportes')

    def __str__(self):
        return self.nombre + ' ' + str(self.cant_jugadores)


class Superficie(models.Model):
    """Modelo para almacenar las superficies de las canchas."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name=_('Nombre'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = _('Superficie')
        verbose_name_plural = _('Superficies')


# Parámetros de localización
class Pais(models.Model):
    """Modelo para almacenar los países."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name=_('Nombre'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = _('País')
        verbose_name_plural = _('Países')


class Provincia(models.Model):
    """Modelo para almacenar las provincias."""
    nombre = models.CharField(max_length=100, verbose_name=_('Nombre'))
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, verbose_name=_('País'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    def __str__(self):
        return self.nombre

    class Meta:
        unique_together = ('nombre', 'pais')
        verbose_name = _('Provincia')
        verbose_name_plural = _('Provincias')


class Localidad(models.Model):
    """Modelo para almacenar las localidades."""
    nombre = models.CharField(max_length=255, verbose_name=_('Nombre'))
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT, verbose_name=_('Provincia'))
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, verbose_name=_('Pais'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    def __str__(self):
        return self.nombre + ', ' + self.provincia.nombre + ', ' + self.pais.nombre

    class Meta:
        unique_together = ('nombre', 'provincia', 'pais')
        verbose_name = _('Localidad')
        verbose_name_plural = _('Localidades')
