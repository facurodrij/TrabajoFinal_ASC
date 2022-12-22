import locale
from datetime import datetime

import pytz
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.forms import model_to_dict
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_softdelete.models import SoftDeleteModel
from num2words import num2words
from simple_history.models import HistoricalRecords

from parameters.models import ClubParameters

locale.setlocale(locale.LC_ALL, 'es_AR.UTF-8')


class Socio(SoftDeleteModel):
    """
    Modelo de socio.
    """
    persona = models.OneToOneField('accounts.Persona', on_delete=models.PROTECT)
    fecha_ingreso = models.DateField(default=datetime.now)
    history = HistoricalRecords()

    def __str__(self):
        return self.persona.__str__()

    def get_categoria(self):
        """
        TODO: Devuelve la categoria del socio en base a su edad.
        """

    def es_titular(self):
        """
        TODO: Devuelve True si el socio es titular.
        """

    def get_estado(self):
        return 'Activo' if self.is_deleted is False else 'Inactivo'

    def get_miembros(self):
        """
        TODO: Devuelve los miembros del socio.
        """

    def get_tipo(self):
        return 'Titular' if self.es_titular() else 'Miembro'

    def get_user(self):
        try:
            return self.user
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
        item['url_editar'] = reverse('admin-socio-editar', kwargs={'pk': self.pk})
        return item

    class Meta:
        verbose_name = 'Socio'
        verbose_name_plural = "Socios"
        ordering = ['id']


class Categoria(models.Model):
    """
    Modelo para almacenar las categorías de los socios.
    """
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    cuota = models.DecimalField(max_digits=10, default=0, decimal_places=2, verbose_name='Cuota')
    edad_desde = models.PositiveSmallIntegerField(default=0, verbose_name='Edad desde')
    edad_hasta = models.PositiveSmallIntegerField(default=0, verbose_name='Edad hasta')
    se_factura = models.BooleanField(default=True, verbose_name='¿Se factura?')

    def __str__(self):
        return self.nombre + ' $' + str(self.cuota)

    def get_rango_edad(self):
        if self.edad_desde == 0 and self.edad_hasta == 0:
            return 'Sin rango'
        if self.edad_hasta > 100:
            return '{}+'.format(self.edad_desde)
        return '{} - {}'.format(self.edad_desde, self.edad_hasta)

    def clean(self):
        # TODO: Validar que no exista una categoria con el mismo rango de edad
        # TODO: Validar que las edades de la categoria no se solapen con otras categorias
        if self.cuota == 0:
            self.se_factura = False
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
        constraints = [
            # Cuota debe ser mayor o igual a 0
            models.CheckConstraint(
                check=models.Q(cuota__gte=0),
                name='cuota_mayor_igual_cero',
                violation_error_message='La cuota debe ser mayor o igual a 0.'
            ),
            # Si cuota es 0, se_factura debe ser False
            models.CheckConstraint(
                check=~(models.Q(cuota=0) & models.Q(se_factura=True)),
                name='cuota_se_factura',
                violation_error_message='Si el precio de la cuota es $0, no se debe incluir en el '
                                        'detalle de la facturación.'
            ),
        ]


class CuotaSocial(SoftDeleteModel):
    """
    Modelo para almacenar las cuotas sociales.
    """
    MESES = (
        (1, 'Enero'),
        (2, 'Febrero'),
        (3, 'Marzo'),
        (4, 'Abril'),
        (5, 'Mayo'),
        (6, 'Junio'),
        (7, 'Julio'),
        (8, 'Agosto'),
        (9, 'Septiembre'),
        (10, 'Octubre'),
        (11, 'Noviembre'),
        (12, 'Diciembre'),
    )

    persona = models.ForeignKey('accounts.Persona', on_delete=models.PROTECT, verbose_name='Persona')
    fecha_emision = models.DateTimeField(default=datetime.now, verbose_name='Fecha de emisión')
    fecha_vencimiento = models.DateTimeField(verbose_name='Fecha de vencimiento', null=True, blank=True)
    periodo_mes = models.PositiveSmallIntegerField(verbose_name='Meses', choices=MESES)
    periodo_anio = models.PositiveIntegerField(verbose_name='Año', validators=[MinValueValidator(1900)])
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Total')
    cargo_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Cargo extra')
    observaciones = models.TextField(verbose_name='Observaciones', null=True, blank=True)
    history = HistoricalRecords()

    def is_pagada(self):
        try:
            if not self.pagocuotasocial.is_deleted:
                return True
            else:
                return False
        except AttributeError:
            return False

    def is_atrasada(self):
        if self.fecha_vencimiento < datetime.now(
                pytz.timezone('America/Argentina/Buenos_Aires')) and not self.is_pagada():
            return True
        return False

    def meses_atraso(self):
        if self.is_atrasada():
            return (datetime.now(pytz.timezone(
                'America/Argentina/Buenos_Aires')).year - self.fecha_vencimiento.year) * 12 + (
                    datetime.now(pytz.timezone(
                        'America/Argentina/Buenos_Aires')).month - self.fecha_vencimiento.month)
        return 0

    def interes(self):
        aumento_por_cuota_vencida = ClubParameters.objects.get(pk=1).aumento_por_cuota_vencida
        if self.is_atrasada():
            return round(self.total * (aumento_por_cuota_vencida / 100) * self.meses_atraso(), 2)
        return 0

    def total_a_pagar(self):
        return round(self.total + self.cargo_extra + self.interes(), 2)

    def get_estado(self):
        if self.is_pagada():
            return 'Pagada'
        elif self.is_deleted:
            return 'Anulada'
        return 'Pendiente'

    def get_fecha_emision(self):
        return self.fecha_emision.strftime('%d/%m/%Y')

    def get_fecha_vencimiento(self):
        return self.fecha_vencimiento.strftime('%d/%m/%Y') if self.fecha_vencimiento else 'Sin vencimiento'

    def get_fecha_pago(self):
        return self.pagocuotasocial.fecha_pago.strftime('%d/%m/%Y') if self.is_pagada() else 'Sin pago'

    def get_periodo(self):
        return datetime.strptime(f'{self.periodo_anio}-{self.periodo_mes}', '%Y-%m').strftime('%B %Y').capitalize()

    def get_subtotal(self):
        return self.total - self.cargo_extra

    def get_motivo_anulacion(self):
        # Obtener reason change en django_simple_history
        motivo = self.history.filter(is_deleted=True).first().history_change_reason
        return motivo if motivo else 'No especificado'

    def get_total_letras(self):
        """
        Obtener el total en letras.
        """
        if self.is_pagada():
            return 'Son: {} pesos argentinos'.format(num2words(self.pagocuotasocial.total_pagado, lang='es'))
        if self.is_deleted:
            return 'Son: {} pesos argentinos'.format(num2words(self.total, lang='es'))
        return 'Son: {} pesos argentinos'.format(num2words(self.total_a_pagar(), lang='es'))

    def get_related_objects(self):
        return self.detallecuotasocial_set.all()

    def toJSON(self):
        item = model_to_dict(self)
        item['persona'] = self.persona.toJSON()
        item['fecha_emision'] = self.fecha_emision.strftime('%d/%m/%Y %H:%M')
        item['fecha_vencimiento'] = self.fecha_vencimiento.strftime(
            '%d/%m/%Y %H:%M') if self.fecha_vencimiento else 'Sin vencimiento'
        item['fecha_pago'] = self.get_fecha_pago()
        item['periodo'] = self.get_periodo()
        item['estado'] = self.get_estado()
        item['subtotal'] = self.get_subtotal()
        return item

    def unique_error_message(self, model_class, unique_check):
        if model_class == type(self) and unique_check == ('persona', 'periodo_mes', 'periodo_anio'):
            return 'Ya existe una cuota social para la persona en el periodo seleccionado.'
        return super(CuotaSocial, self).unique_error_message(model_class, unique_check)

    def clean(self):
        # Un socio no puede tener generada una cuota social el mismo mes y año que otra.
        if CuotaSocial.global_objects.filter(persona=self.persona,
                                             periodo_mes=self.periodo_mes,
                                             periodo_anio=self.periodo_anio).exclude(pk=self.pk).exists():
            raise ValidationError('Ya existe una cuota social generada para el mes y año seleccionado.')

    # TODO: Consultar si es necesario verificar esto.
    # if self.pk is None:
    #     # Si es una nueva cuota, verificar que la anterior sea del mes anterior.
    #     cuota_anterior = CuotaSocial.objects.filter(
    #         persona=self.persona).order_by(
    #         '-periodo_anio', '-periodo_mes').first()
    #     if cuota_anterior:
    #         if self.periodo_anio == cuota_anterior.periodo_anio:
    #             if self.periodo_mes != cuota_anterior.periodo_mes + 1:
    #                 raise ValidationError('La cuota debe ser del mes siguiente a la anterior.')
    #         elif self.periodo_anio != cuota_anterior.periodo_anio + 1:
    #             raise ValidationError('La cuota debe ser del mes siguiente a la anterior.')
    # else:
    #     # Si es una cuota existente, verificar que la anterior sea del mes anterior.
    #     cuota_anterior = CuotaSocial.objects.filter(persona=self.persona).exclude(pk=self.pk).order_by(
    #         '-periodo_anio', '-periodo_mes').first()
    #     if cuota_anterior:
    #         if self.periodo_anio == cuota_anterior.periodo_anio:
    #             if self.periodo_mes != cuota_anterior.periodo_mes + 1:
    #                 raise ValidationError('La cuota debe ser del mes siguiente a la anterior.')
    #         elif self.periodo_anio != cuota_anterior.periodo_anio + 1:
    #             raise ValidationError('La cuota debe ser del mes siguiente a la anterior.') Los periodos de las
    #             cuotas por cada socio deben ser consecutivos.

    class Meta:
        verbose_name = 'Cuota social'
        verbose_name_plural = 'Cuotas sociales'
        unique_together = ('persona', 'periodo_mes', 'periodo_anio')
        constraints = [
            # Validar que el total sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(total__gte=0),
                                   name='cuota_social_total_valido',
                                   violation_error_message=_(
                                       'Total: El total debe ser mayor o igual a 0.')),
            # Validar que el cargo extra sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(cargo_extra__gte=0),
                                   name='cuota_social_cargo_extra_valido',
                                   violation_error_message=_(
                                       'Cargo extra: El cargo extra debe ser mayor o igual a 0.')),
            # TODO: Consultar si es necesario validar esto.
            # Validar que Fecha de vencimiento no puede ser menor a la fecha de emisión.
            # models.CheckConstraint(check=models.Q(fecha_vencimiento__gte=models.F('fecha_emision')),
            #                        name='cuota_social_fecha_vencimiento_valido',
            #                        violation_error_message=_(
            #                            'Fecha de vencimiento: La fecha de vencimiento no puede '
            #                            'ser menor a la fecha de emisión.')),
            # Validar que total_pagado no puede ser menor al total.
        ]


class DetalleCuotaSocial(SoftDeleteModel):
    """
    Modelo para almacenar los detalles de las cuotas sociales.
    """
    cuota_social = models.ForeignKey('socios.CuotaSocial', on_delete=models.PROTECT, verbose_name='Cuota social')
    socio = models.ForeignKey('socios.Socio', on_delete=models.PROTECT, verbose_name='Socio')
    nombre_completo = models.CharField(max_length=100, verbose_name='Nombre completo')
    categoria = models.CharField(max_length=50, verbose_name='Categoría')
    cuota = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Cuota')
    cargo_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Cargo extra')
    total_parcial = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total parcial')

    def toJSON(self):
        item = model_to_dict(self)
        item['cuota_social'] = self.cuota_social.toJSON()
        item['socio'] = self.socio.toJSON()
        return item

    def clean(self):
        super(DetalleCuotaSocial, self).clean()
        if self.cuota_social.fecha_pago:
            raise ValidationError('No se puede modificar un detalle de cuota social que ya ha sido pagada.')

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.cuota = self.socio.categoria.cuota
        self.total_parcial = self.cuota + self.cargo_extra
        super(DetalleCuotaSocial, self).save(force_insert, force_update, using, update_fields)

    class Meta:
        verbose_name = 'Detalle de cuota social'
        verbose_name_plural = 'Detalles de cuotas sociales'
        constraints = [
            # Validar que la cuota sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(cuota__gte=0),
                                   name='detalle_cuota_social_cuota_valida',
                                   violation_error_message=_(
                                       'Cuota: La cuota debe ser mayor o igual a 0.')),
            # Validar que el cargo extra sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(cargo_extra__gte=0),
                                   name='detalle_cuota_social_cargo_extra_valido',
                                   violation_error_message=_(
                                       'Cargo extra: El cargo extra debe ser mayor o igual a 0.')),
            # Validar que el total parcial sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(total_parcial__gte=0),
                                   name='detalle_cuota_social_total_parcial_valido',
                                   violation_error_message=_(
                                       'Total parcial: El total parcial debe ser mayor o igual a 0.')),
        ]


class PagoCuotaSocial(SoftDeleteModel):
    """
    Modelo para almacenar los pagos de las cuotas sociales.
    """
    cuota_social = models.OneToOneField('socios.CuotaSocial', on_delete=models.PROTECT, verbose_name='Cuota social')
    medio_pago = models.ForeignKey('parameters.MedioPago', on_delete=models.PROTECT, verbose_name='Medio de pago')
    fecha_pago = models.DateField(verbose_name='Fecha de pago')
    total_pagado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total pagado')

    def meses_atraso(self):
        return self.fecha_pago.month - self.cuota_social.periodo_mes

    def interes_aplicado(self):
        return self.total_pagado - self.cuota_social.total

    def toJSON(self):
        item = model_to_dict(self)
        item['cuota_social'] = self.cuota_social.toJSON()
        return item

    def clean(self):
        super(PagoCuotaSocial, self).clean()
        if self.cuota_social.fecha_pago:
            raise ValidationError('No se puede modificar un pago de cuota social que ya ha sido pagada.')

    class Meta:
        verbose_name = 'Pago de cuota social'
        verbose_name_plural = 'Pagos de cuotas sociales'
        constraints = [
            # Validar que el total pagado sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(total_pagado__gte=0),
                                   name='pago_cuota_social_total_pagado_valido',
                                   violation_error_message=_(
                                       'Total pagado: El total pagado debe ser mayor o igual a 0.')),
        ]
