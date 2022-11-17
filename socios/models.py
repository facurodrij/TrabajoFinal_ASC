from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _
from django_softdelete.models import SoftDeleteModel

from accounts.models import PersonaAbstract


class Socio(SoftDeleteModel):
    """
    Modelo de socio.
    """
    persona = models.OneToOneField('accounts.Persona', on_delete=models.PROTECT)
    categoria = models.ForeignKey('socios.Categoria', on_delete=models.PROTECT)
    estado = models.ForeignKey('socios.Estado', on_delete=models.PROTECT)
    fecha_ingreso = models.DateField(default=datetime.now)
    socio_titular = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True)
    parentesco = models.ForeignKey('parameters.Parentesco', on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return self.persona.__str__()

    def es_titular(self):
        return True if self.socio_titular_id is None else False

    def get_miembros(self):
        return Socio.global_objects.filter(socio_titular=self)

    def get_parentesco(self):
        return 'Titular' if self.es_titular() else self.parentesco

    def get_tipo(self):
        return 'Titular' if self.es_titular() else 'Miembro'

    def get_user(self):
        try:
            return self.persona.user
        except ObjectDoesNotExist:
            return None

    def get_related_objects(self):
        if self.es_titular():
            return self.get_miembros()
        return []

    def get_antiguedad(self):
        # Si supera el año, mostrar en años, si no en meses
        if (datetime.now().year - self.fecha_ingreso.year) > 0:
            return '{} años'.format(datetime.now().year - self.fecha_ingreso.year)
        else:
            return '{} meses'.format(datetime.now().month - self.fecha_ingreso.month)

    def toJSON(self):
        item = model_to_dict(self)
        item['__str__'] = self.__str__()
        return item

    def clean(self):
        # Si tuviera miembros, asignarle el mismo estado
        if self.es_titular():
            if self.get_miembros().exists():
                for miembro in self.get_miembros():
                    miembro.estado = self.estado
                    miembro.save()

        # Un socio no puede ser miembro de otro miembro
        if not self.es_titular():
            if not self.socio_titular.es_titular():
                raise ValidationError(_('Un socio no puede ser miembro de otro miembro.'))

        # TODO: Si el socio tiene deudas pendientes, no puede ser eliminado

    class Meta:
        verbose_name = 'Socio'
        verbose_name_plural = "Socios"
        ordering = ['id']
        constraints = [
            # Validar que el socio titular no sea el mismo socio
            models.CheckConstraint(
                check=~models.Q(socio_titular=models.F('id')),
                name='socio_titular_distinto_socio'
            ),
            # Validar si socio_titular es nulo, parentesco también lo es y viceversa
            models.CheckConstraint(
                check=((models.Q(socio_titular__isnull=True) & models.Q(parentesco__isnull=True))
                       | (models.Q(socio_titular__isnull=False) & models.Q(parentesco__isnull=False))),
                name='socio_titular_parentesco'
            ),
        ]


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
        item['__str__'] = self.__str__()
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
