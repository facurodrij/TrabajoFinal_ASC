from django.db import models
from django_softdelete.models import SoftDeleteModel, SoftDeleteManager
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from accounts.models import Persona, PersonaAbstract


class Socio(SoftDeleteModel):
    """
    Modelo de socio.
    """
    persona = models.OneToOneField(Persona, on_delete=models.PROTECT)
    categoria = models.ForeignKey('socios.Categoria', on_delete=models.PROTECT)
    estado = models.ForeignKey('socios.Estado', on_delete=models.PROTECT)

    def __str__(self):
        return self.persona.get_full_name()

    def get_user(self):
        try:
            return self.persona.user
        except ObjectDoesNotExist:
            return None

    class Meta:
        verbose_name = 'Socio'
        verbose_name_plural = "Socios"
        ordering = ['id']


class Miembro(PersonaAbstract):
    """
    Modelo de miembro de familia.
    """
    socio = models.ForeignKey(Socio, on_delete=models.PROTECT)
    parentesco = models.ForeignKey('parameters.Parentesco', on_delete=models.PROTECT)
    categoria = models.ForeignKey('socios.Categoria', on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Miembro'
        verbose_name_plural = "Miembros"


class Categoria(models.Model):
    """
    Modelo para almacenar las categorías de los socios.
    """
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    tipo = models.ForeignKey('socios.Tipo', on_delete=models.PROTECT)
    cuota = models.DecimalField(max_digits=10, default=0.10, decimal_places=2, verbose_name='Cuota')
    edad_desde = models.PositiveSmallIntegerField(default=0, verbose_name='Edad desde')
    edad_hasta = models.PositiveSmallIntegerField(default=0, verbose_name='Edad hasta')

    def __str__(self):
        return self.nombre + ' - ' + self.tipo.nombre

    def clean(self):
        if self.edad_desde > self.edad_hasta:
            raise ValidationError('La edad "desde" debe ser menor que la edad "hasta".')
        if self.edad_desde == self.edad_hasta:
            raise ValidationError('Las edades ingresadas no deben ser iguales.')

    class Meta:
        unique_together = ('nombre', 'tipo')
        verbose_name = 'Categoría de socio'
        verbose_name_plural = 'Categorías de socios'


class Tipo(models.Model):
    """
    Modelo para almacenar los tipos de socios.
    """
    nombre = models.CharField(max_length=255, unique=True, verbose_name='Nombre')
    code = models.CharField(max_length=2, unique=True, verbose_name='Código')
    admite_miembro = models.BooleanField(default=False, verbose_name='¿Admite miembros?')
    cant_max_miembros = models.PositiveSmallIntegerField(default=5, verbose_name='Cantidad máxima de miembros')

    def __str__(self):
        if self.admite_miembro:
            return self.nombre + ' (max. ' + str(self.cant_max_miembros) + ' miembros)'
        return self.nombre

    def clean(self):
        if self.admite_miembro and self.cant_max_miembros < 2:
            raise ValidationError('La cantidad máxima de miembros debe ser mayor o igual a 2.')
        if not self.admite_miembro and self.cant_max_miembros > 0:
            raise ValidationError('Si no admite miembros, la cantidad máxima de miembros debe ser 0.')

    class Meta:
        verbose_name = 'Tipo de socio'
        verbose_name_plural = 'Tipos de socios'


class Estado(models.Model):
    """
    Modelo para almacenar los estados de los socios.
    """
    nombre = models.CharField(max_length=50, unique=True, verbose_name='Nombre')
    descripcion = models.CharField(max_length=255, verbose_name='Descripción')
    code = models.CharField(max_length=2, unique=True, verbose_name='Código')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Estado de socio'
        verbose_name_plural = 'Estados de socios'
