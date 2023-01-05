from django.db import models
from django.utils.translation import gettext_lazy as _


# PARÁMETROS DEL SISTEMA
# Parámetros para la app Socios
class Parentesco(models.Model):
    """
    Modelo para almacenar los parentescos de los miembros de la familia.
    """
    nombre = models.CharField(max_length=50, verbose_name=_('Nombre'))
    menor_al_titular = models.BooleanField(default=True, verbose_name=_('Debe ser menor que el titular'))

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = _('Parentesco')
        verbose_name_plural = _('Parentescos')


class ClubParameters(models.Model):
    """
    Modelo para almacenar las reglas establecidas para los socios.
    Las reglas las establece el administrador del club.
    """
    club = models.OneToOneField('core.Club', on_delete=models.CASCADE, verbose_name=_('Club'))
    edad_minima_titular = models.PositiveSmallIntegerField(
        default=16,
        verbose_name=_('Edad mínima para no necesitar tutor'),
        help_text=_('Edad mínima para no necesitar tutor'))
    dia_emision_cuota = models.PositiveSmallIntegerField(
        default=7,
        verbose_name=_('Día de emisión'))
    dia_vencimiento_cuota = models.PositiveSmallIntegerField(
        default=28,
        verbose_name=_('Día de vencimiento'))
    cantidad_maxima_cuotas_pendientes = models.PositiveSmallIntegerField(
        default=3,
        verbose_name=_('Cantidad máxima de cuotas pendientes'))
    aumento_por_cuota_vencida = models.DecimalField(
        default=10.0,
        max_digits=5,
        decimal_places=2,
        verbose_name=_('Porcentaje de aumento por cuota vencida'))

    class Meta:
        verbose_name = _('Regla de socio')
        verbose_name_plural = _('Reglas de socios')


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


class Deporte(models.Model):
    """Modelo para almacenar los deportes."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name=_('Nombre'))

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = _('Deporte')
        verbose_name_plural = _('Deportes')


class Superficie(models.Model):
    """Modelo para almacenar las superficies."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name=_('Nombre'))

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = _('Superficie')
        verbose_name_plural = _('Superficies')
