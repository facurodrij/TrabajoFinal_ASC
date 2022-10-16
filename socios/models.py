from django.db import models
from django_softdelete.models import SoftDeleteModel, SoftDeleteManager
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from accounts.models import User, Persona


class SocioIndividual(SoftDeleteModel):
    """
    Modelo de socio individual.
    """
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    club = models.ForeignKey('core.Club', on_delete=models.PROTECT)
    categoria = models.ForeignKey('socios.Categoria', on_delete=models.PROTECT)
    estado = models.ForeignKey('socios.Estado', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_full_name()

    def is_titular(self):
        try:
            if self.miembroregistrado.is_titular:
                return True
            else:
                return False
        except ObjectDoesNotExist:
            """
            Si no tiene relación con la tabla MiembroRegistrado,
            es titular porque no forma parte de ningún grupo familiar.
            """
            return True

    class Meta:
        verbose_name = 'Socio individual'
        verbose_name_plural = "Socios individuales"
        ordering = ['id']


class GrupoFamiliar(SoftDeleteModel):
    """
    Modelo de grupo familiar.
    """
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    def get_estado(self):
        """
        Devuelve el estado del grupo familiar.
        """
        miembro_titular = self.miembroregistrado_set.filter(is_titular=True).first()
        if miembro_titular:
            return miembro_titular.socio.estado.is_active

    class Meta:
        verbose_name = 'Grupo familiar'
        verbose_name_plural = "Grupos familiares"
        ordering = ['id']


class MiembroRegistrado(SoftDeleteModel):
    """
    Modelo de miembro registrado.
    """
    socio = models.OneToOneField(SocioIndividual, on_delete=models.PROTECT)
    gp_familiar = models.ForeignKey(GrupoFamiliar, on_delete=models.PROTECT)
    is_titular = models.BooleanField(default=False, verbose_name='¿Es titular?')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.socio.user.get_full_name()

    class Meta:
        unique_together = ('gp_familiar', 'is_titular')
        verbose_name = 'Miembro registrado'
        verbose_name_plural = "Miembros registrados"
        ordering = ['id']


class MiembroNoRegistrado(SoftDeleteModel):
    """
    El miembro no registrado es un miembro familiar que no tiene cuenta (usuario y email).
    """
    persona = models.OneToOneField(Persona, on_delete=models.PROTECT)
    categoria = models.ForeignKey('socios.Categoria', on_delete=models.PROTECT)
    gp_familiar = models.ForeignKey(GrupoFamiliar, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.persona.get_full_name()

    class Meta:
        verbose_name = 'Miembro no registrado'
        verbose_name_plural = "Miembros no registrados"
        ordering = ['id']


class Categoria(models.Model):
    """
    Modelo para almacenar las categorías de los socios.
    """
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    tipo = models.ForeignKey('socios.Tipo', on_delete=models.PROTECT)
    cuota = models.DecimalField(max_digits=10, default=0.10, decimal_places=2, verbose_name='Cuota')
    edad_desde = models.PositiveSmallIntegerField(default=0, verbose_name='Edad desde')
    edad_hasta = models.PositiveSmallIntegerField(default=0, verbose_name='Edad hasta')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre + ' - ' + self.tipo.nombre

    def clean(self):
        if self.edad_desde > self.edad_hasta:
            raise ValidationError('La edad "desde" debe ser menor que la edad "hasta".')
        if self.edad_desde == self.edad_hasta:
            raise ValidationError('Las edades ingresadas no deben ser iguales.')

    # TODO: Obtener todas la categorías posibles que puede elegir un socio según su edad.

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    # ESTADOS = (
    #     ('FA', 'Falta aprobación'),
    #     ('AP', 'Aprobado'),
    #     ('RE', 'Rechazado'),
    # )
    nombre = models.CharField(max_length=50, unique=True, verbose_name='Nombre')
    descripcion = models.CharField(max_length=255, verbose_name='Descripción')
    code = models.CharField(max_length=2, unique=True, verbose_name='Código')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Estado de socio'
        verbose_name_plural = 'Estados de socios'
