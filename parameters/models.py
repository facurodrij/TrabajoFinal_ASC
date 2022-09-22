from django.db import models
from django.utils.translation import gettext_lazy as _


# Parametros para las canchas
class Superficie(models.Model):
    nombre = models.CharField(max_length=255, verbose_name=_('Nombre'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = _('Superficie')
        verbose_name_plural = _('Superficies')


# Parametros de localización
class Pais(models.Model):
    nombre = models.CharField(max_length=255, unique=True, verbose_name=_('Nombre'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = _('Pais')
        verbose_name_plural = _('Paises')


class Provincia(models.Model):
    nombre = models.CharField(max_length=255, verbose_name=_('Nombre'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, verbose_name=_('Pais'))

    def __str__(self):
        return self.nombre

    class Meta:
        unique_together = ('nombre', 'pais')
        verbose_name = _('Provincia')
        verbose_name_plural = _('Provincias')


class Localidad(models.Model):
    nombre = models.CharField(max_length=255, verbose_name=_('Nombre'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT, verbose_name=_('Provincia'))
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, verbose_name=_('Pais'))

    def __str__(self):
        return self.nombre

    class Meta:
        unique_together = ('nombre', 'provincia', 'pais')
        verbose_name = _('Localidad')
        verbose_name_plural = _('Localidades')


""" Guardar en la base de datos Pais, Provincia y Localidad """
paises = [
    'Argentina',
]
provincias = [
    ['Buenos Aires', 'Argentina'],
    ['CABA', 'Argentina'],
    ['Catamarca', 'Argentina'],
    ['Chaco', 'Argentina'],
    ['Chubut', 'Argentina'],
    ['Córdoba', 'Argentina'],
    ['Corrientes', 'Argentina'],
    ['Entre Ríos', 'Argentina'],
    ['Formosa', 'Argentina'],
    ['Jujuy', 'Argentina'],
    ['La Pampa', 'Argentina'],
    ['La Rioja', 'Argentina'],
    ['Mendoza', 'Argentina'],
    ['Misiones', 'Argentina'],
    ['Neuquén', 'Argentina'],
    ['Río Negro', 'Argentina'],
    ['Salta', 'Argentina'],
    ['San Juan', 'Argentina'],
    ['San Luis', 'Argentina'],
    ['Santa Cruz', 'Argentina'],
    ['Santa Fe', 'Argentina'],
    ['Santiago del Estero', 'Argentina'],
    ['Tierra del Fuego, Antártida e Islas del Atlántico Sur', 'Argentina'],
    ['Tucumán', 'Argentina'],
]
localidades = [
    ['La Plata', 'Buenos Aires', 'Argentina'],
    ['Mar del Plata', 'Buenos Aires', 'Argentina'],
    ['Rosario', 'Santa Fe', 'Argentina'],
    ['Santa Fe', 'Santa Fe', 'Argentina'],
    ['San Miguel de Tucumán', 'Tucumán', 'Argentina'],
    ['San Salvador de Jujuy', 'Jujuy', 'Argentina'],
    ['Resistencia', 'Chaco', 'Argentina'],
    ['Posadas', 'Misiones', 'Argentina'],
    ['San Juan', 'San Juan', 'Argentina'],
    ['Córdoba', 'Córdoba', 'Argentina'],
    ['Paraná', 'Entre Ríos', 'Argentina'],
    ['Neuquén', 'Neuquén', 'Argentina'],
    ['Bahía Blanca', 'Buenos Aires', 'Argentina'],
    ['Comodoro Rivadavia', 'Chubut', 'Argentina'],
    ['San Fernando del Valle de Catamarca', 'Catamarca', 'Argentina'],
    ['San Luis', 'San Luis', 'Argentina'],
    ['Río Gallegos', 'Santa Cruz', 'Argentina'],
    ['Mendoza', 'Mendoza', 'Argentina'],
    ['San Rafael', 'Mendoza', 'Argentina'],
    ['San Fernando del Valle de Catamarca', 'Catamarca', 'Argentina'],
]
for pais in paises:
    try:
        Pais.objects.get(nombre=pais)
    except Pais.DoesNotExist:
        Pais.objects.create(nombre=pais)
for provincia in provincias:
    try:
        Provincia.objects.get(nombre=provincia[0])
    except Provincia.DoesNotExist:
        Provincia.objects.create(nombre=provincia[0], pais=Pais.objects.get(nombre=provincia[1]))
for localidad in localidades:
    try:
        Localidad.objects.get(nombre=localidad[0])
    except Localidad.DoesNotExist:
        Localidad.objects.create(nombre=localidad[0],
                                 provincia=Provincia.objects.get(nombre=localidad[1]),
                                 pais=Pais.objects.get(nombre=localidad[2]))
