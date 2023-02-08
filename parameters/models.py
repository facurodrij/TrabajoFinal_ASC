from django.db import models
from django.utils.translation import gettext_lazy as _


# PARÁMETROS DEL SISTEMA
class MedioPago(models.Model):
    """
    Modelo para almacenar los medios de pago.
    """
    nombre = models.CharField(max_length=50, verbose_name=_('Nombre'))

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = _('Medio de pago')
        verbose_name_plural = _('Medios de pago')


# Parámetros para la app Accounts
class Sexo(models.Model):
    """Modelo para almacenar los sexos de los usuarios."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name=_('Nombre'))

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = _('Sexo')
        verbose_name_plural = _('Sexos')


# Parámetros de localización
class Pais(models.Model):
    """Modelo para almacenar los países."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name=_('Nombre'))

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = _('País')
        verbose_name_plural = _('Países')


class Provincia(models.Model):
    """Modelo para almacenar las provincias."""
    nombre = models.CharField(max_length=100, verbose_name=_('Nombre'))
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, verbose_name=_('País'))

    def __str__(self):
        return self.nombre

    class Meta:
        unique_together = ('nombre', 'pais')
        verbose_name = _('Provincia')
        verbose_name_plural = _('Provincias')


class Departamento(models.Model):
    nombre = models.CharField(max_length=100, verbose_name=_('Nombre'))
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT, verbose_name=_('Provincia'))

    def __unicode__(self):
        return self.nombre

    class Meta:
        unique_together = ('nombre', 'provincia')
        verbose_name = _('Departamento')
        verbose_name_plural = _('Departamentos')


class Municipio(models.Model):
    nombre = models.CharField(max_length=255)
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT)

    def __unicode__(self):
        return self.nombre

    class Meta:
        verbose_name = _('Municipio')
        verbose_name_plural = _('Municipios')


class Localidad(models.Model):
    nombre = models.CharField(max_length=255)
    categoria = models.CharField(max_length=50)
    departamento = models.ForeignKey(Departamento, on_delete=models.PROTECT, null=True)
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, null=True)
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT)

    def __str__(self):
        localidad = self.nombre
        if self.municipio and self.municipio.nombre != self.nombre:
            localidad += ', ' + self.municipio.nombre
        if self.departamento and self.departamento.nombre != self.nombre:
            localidad += ', ' + self.departamento.nombre
        localidad += ', ' + self.provincia.nombre
        return localidad

    class Meta:
        verbose_name_plural = "Localidades"
        unique_together = ("nombre", "provincia", "departamento", "municipio")
