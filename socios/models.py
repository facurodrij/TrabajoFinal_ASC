from datetime import datetime
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Q, F
from django.forms import model_to_dict
from django_softdelete.models import SoftDeleteModel, SoftDeleteManager
from django.utils.translation import gettext_lazy as _

from accounts.models import Persona, PersonaAbstract


class Socio(SoftDeleteModel):
    """
    Modelo de socio.
    """
    persona = models.OneToOneField(Persona, on_delete=models.PROTECT)
    categoria = models.ForeignKey('socios.Categoria', on_delete=models.PROTECT)
    estado = models.ForeignKey('socios.Estado', on_delete=models.PROTECT)

    def __str__(self):
        return self.persona.__str__()

    def get_user(self):
        try:
            return self.persona.user
        except ObjectDoesNotExist:
            return None

    def get_related_objects(self):
        """
        Devuelve una lista de objetos relacionados con el socio.
        """
        try:
            miembro = Miembro.global_objects.filter(socio=self)
            # Queryset to list
            miembro = list(miembro)
            return miembro
        except ObjectDoesNotExist:
            return []

    def restore(self, cascade=None):
        # Si el socio tiene Persona eliminada, no puede ser restaurado
        persona = Persona.global_objects.get(pk=self.persona.pk)
        if persona.is_deleted:
            raise ValidationError('No se puede restaurar el socio porque la persona está eliminada.')

        # Si el socio es miembro de un grupo familiar, no puede ser restaurado
        try:
            if not self.persona.miembro.is_deleted:
                raise ValidationError(
                    'No es posible restaurar el socio: '
                    '{}, porque ya es miembro de otro socio.'.format(self.persona.get_full_name()))
        except ObjectDoesNotExist:
            pass
        super(Socio, self).restore(cascade=cascade)

    # TODO: Si el socio tiene deudas pendientes, no puede ser eliminado

    def clean(self):
        super(Socio, self).clean()
        # Socio no puede ser miembro
        try:
            if not self.persona.miembro.is_deleted:
                raise ValidationError(
                    'La persona {} ya es miembro de otro socio.'.format(self.persona.get_full_name()))
        except ObjectDoesNotExist:
            pass

    class Meta:
        verbose_name = 'Socio'
        verbose_name_plural = "Socios"
        ordering = ['id']


class Miembro(SoftDeleteModel):
    """
    Modelo de miembro de familia.
    """
    persona = models.OneToOneField(Persona, on_delete=models.PROTECT, verbose_name='Datos del miembro')
    socio = models.ForeignKey(Socio, on_delete=models.PROTECT, verbose_name='Socio a cargo')
    parentesco = models.ForeignKey('parameters.Parentesco', on_delete=models.PROTECT, verbose_name='Parentesco con socio')
    categoria = models.ForeignKey('socios.Categoria', on_delete=models.PROTECT)

    def __str__(self):
        return self.persona.__str__()

    def restore(self, cascade=None):
        # Si el miembro tiene Persona eliminada, no puede ser restaurado
        persona = Persona.global_objects.get(pk=self.persona.pk)
        if persona.is_deleted:
            raise ValidationError('No se puede restaurar el miembro porque la persona está eliminada.')

        # Si el miembro es socio, no puede ser restaurado
        try:
            if not self.persona.socio.is_deleted:
                raise ValidationError(
                    'No es posible restaurar el miembro: '
                    '{}, porque ya es socio.'.format(self.persona.get_full_name()))
        except ObjectDoesNotExist:
            pass
        super(Miembro, self).restore(cascade=cascade)

    def clean(self):
        # Miembro no puede ser socio
        try:
            if not self.persona.socio.is_deleted:
                raise ValidationError('La persona {} ya es socio.'.format(self.persona.get_full_name()))
        except ObjectDoesNotExist:
            pass

    # Miembro hereda el atributo estado de su socio
    @property
    def estado(self):
        return self.socio.estado

    class Meta:
        verbose_name = 'Miembro'
        verbose_name_plural = "Miembros"


class Categoria(models.Model):
    """
    Modelo para almacenar las categorías de los socios.
    """
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    cuota = models.DecimalField(max_digits=10, default=0.10, decimal_places=2, verbose_name='Cuota')
    edad_desde = models.PositiveSmallIntegerField(default=0, verbose_name='Edad desde')
    edad_hasta = models.PositiveSmallIntegerField(default=0, verbose_name='Edad hasta')

    def __str__(self):
        return self.nombre + ' $' + str(self.cuota)

    def clean(self):
        if self.edad_desde > self.edad_hasta:
            raise ValidationError('La edad "desde" debe ser menor que la edad "hasta".')
        if self.edad_desde == self.edad_hasta:
            raise ValidationError('Las edades ingresadas no deben ser iguales.')

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'


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
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'


class SolicitudSocio(PersonaAbstract):
    """
    Modelo para almacenar las solicitudes de socios.
    """
    dni = models.CharField(max_length=8, verbose_name='DNI')
    email = models.EmailField(max_length=255, verbose_name='Email')
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, verbose_name='Categoría')
    is_aprobado = models.BooleanField(default=False, verbose_name='Aprobado')

    def get_estado(self):
        if self.is_aprobado:
            return 'Aprobado'
        elif self.is_deleted:
            return 'Rechazado'
        return 'Pendiente'

    def toJSON(self):
        item = model_to_dict(self, exclude=['imagen', 'sexo', 'is_aprobado', 'is_deleted', 'deleted_at'])
        item['estado'] = self.get_estado()
        item['categoria'] = self.categoria.toJSON()
        item['edad'] = self.get_edad()
        item['sexo'] = self.sexo.nombre
        item['imagen'] = self.get_imagen()
        return item

    class Meta:
        verbose_name = 'Solicitud de socio'
        verbose_name_plural = 'Solicitudes de socios'
        constraints = [
            # Validar que el DNI solo contenga números, tenga al menos 7 dígitos y no comience con 0.
            models.CheckConstraint(check=models.Q(dni__regex=r'^[1-9][0-9]{6,}$'),
                                   name='solicitud_dni_valido',
                                   violation_error_message=_(
                                       'DNI: El DNI debe contener solo números, '
                                       'tener al menos 7 dígitos y no comenzar con 0.')),
            # Validar que el nombre y el apellido solo contengan letras y espacios.
            models.CheckConstraint(check=models.Q(nombre__regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$'),
                                   name='solicitud_nombre_valido',
                                   violation_error_message=_(
                                       'Nombre: El nombre solo puede contener letras y espacios.')),
            models.CheckConstraint(check=models.Q(apellido__regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]+$'),
                                   name='solicitud_apellido_valido',
                                   violation_error_message=_(
                                       'Apellido: El apellido solo puede contener letras y espacios.')),
            # Validar que la fecha de nacimiento no sea mayor a la fecha actual.
            models.CheckConstraint(check=models.Q(fecha_nacimiento__lte=datetime.now().date()),
                                   name='solicitud_fecha_nacimiento_valida',
                                   violation_error_message=_(
                                       'Fecha de nacimiento: La fecha de nacimiento no puede ser '
                                       'mayor a la fecha actual.')),
        ]
