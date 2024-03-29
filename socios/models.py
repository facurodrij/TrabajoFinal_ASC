import locale
from datetime import datetime

import pytz
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.forms import model_to_dict
from django.urls import reverse
from django.utils import timezone
from django_softdelete.models import SoftDeleteModel
from num2words import num2words
from simple_history.models import HistoricalRecords

locale.setlocale(locale.LC_ALL, 'es_AR.UTF-8')


class Parameters(models.Model):
    """
    Modelo para almacenar las reglas establecidas para los socios.
    """
    club = models.OneToOneField('core.Club', on_delete=models.PROTECT, verbose_name='Club',
                                related_name='socio_parameters')
    edad_minima_titular = models.PositiveSmallIntegerField(
        default=16,
        verbose_name='Edad mínima para no necesitar tutor',
        help_text='Edad mínima para no necesitar tutor')
    dia_emision_cuota = models.PositiveSmallIntegerField(
        default=7,
        verbose_name='Día de emisión')
    dia_vencimiento_cuota = models.PositiveSmallIntegerField(
        default=28,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        verbose_name='Día de vencimiento')
    cantidad_maxima_cuotas_pendientes = models.PositiveSmallIntegerField(
        default=3,
        verbose_name='Cantidad máxima de cuotas pendientes')
    aumento_por_cuota_vencida = models.DecimalField(
        default=10.0,
        max_digits=5,
        decimal_places=2,
        verbose_name='Porcentaje de aumento por cuota vencida')
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Parámetro de socio'
        verbose_name_plural = 'Parámetros de socios'


class Socio(SoftDeleteModel):
    """
    Modelo de socio.
    """
    persona = models.OneToOneField('core.Persona', on_delete=models.PROTECT)
    user = models.OneToOneField('accounts.User', on_delete=models.PROTECT, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.persona.__str__()

    def get_ID_display(self):
        if self.persona.es_titular():
            return self.pk
        try:
            return '{}-{}'.format(self.persona.persona_titular.socio.pk, self.pk)
        except (AttributeError, ObjectDoesNotExist):
            return self.pk

    def get_ESTADO_display(self):
        if self.is_deleted:
            return 'Inactivo'
        return 'Activo'

    def get_categoria(self):
        """
        Devuelve la categoria del socio con base a su edad.
        """
        for categoria in Categoria.objects.all().order_by('edad_minima'):
            if categoria.edad_minima <= self.persona.get_edad() <= categoria.edad_maxima:
                return categoria
            # En la ultima categoría, si la edad es mayor a la maxima, devolver la ultima categoría
            if categoria == Categoria.objects.last():
                return categoria
        return None

    def grupo_familiar(self):
        """
        Devuelve el grupo familiar del socio.
        """
        if self.persona.es_titular():
            return [self] + self.get_miembros()
        else:
            if self.persona.persona_titular.get_socio():
                if self.persona.persona_titular.get_socio().is_deleted:
                    return self.persona.persona_titular.get_socio().get_miembros()
                return [self.persona.persona_titular.socio] + self.persona.persona_titular.socio.get_miembros()
            personas = self.persona.persona_titular.persona_set.exclude(socio__is_deleted=True).exclude(
                socio__isnull=True)
            return [persona.socio for persona in personas]

    def get_miembros(self):
        """
        Devuelve los socios miembros del titular.
        """
        personas = self.persona.persona_set.exclude(socio__is_deleted=True).exclude(socio__isnull=True)
        return [persona.socio for persona in personas]

    def get_user(self):
        try:
            return self.user if self.user.is_active else None
        except (AttributeError, ObjectDoesNotExist):
            return None

    def get_related_objects(self):
        if self.persona.es_titular():
            return self.get_miembros()
        return []

    def delete(self, cascade=None, *args, **kwargs):
        # cascade = get_settings()['cascade']
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
        self.after_delete()
        if cascade:
            self.delete_related_objects()

    def get_change_reason(self):
        return self.history.last().history_change_reason if self.history.last() else 'Sin motivo'

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
    cuota = models.DecimalField(max_digits=10, default=0, decimal_places=2, verbose_name='Precio de la cuota')
    edad_minima = models.PositiveSmallIntegerField(default=0, verbose_name='Edad mínima')
    edad_maxima = models.PositiveSmallIntegerField(default=0, verbose_name='Edad máxima')
    history = HistoricalRecords()

    def __str__(self):
        if self.cuota > 0:
            return '{} - ${}'.format(self.nombre, self.cuota)
        return self.nombre

    def se_factura(self):
        return True if self.cuota > 0 else False

    def get_rango_edad(self):
        if self.edad_minima == 0 and self.edad_maxima == 0:
            return 'Sin rango'
        if self.edad_maxima >= 100:
            return '{}+'.format(self.edad_minima)
        return '{} - {}'.format(self.edad_minima, self.edad_maxima)

    def clean(self):
        # Validar que la edad mínima no sea mayor a la edad máxima
        if self.edad_minima > self.edad_maxima:
            raise ValidationError('La edad "desde" debe ser menor que la edad "hasta".')

        # Validar que las edades no se crucen con otras categorias
        if self.edad_minima > 0 or self.edad_maxima > 0:
            categorias = Categoria.objects.filter(edad_minima__lte=self.edad_minima,
                                                  edad_maxima__gte=self.edad_minima).exclude(pk=self.pk)
            if categorias.exists():
                raise ValidationError('Ya existe una categoría con el mismo rango de edad.')
            categorias = Categoria.objects.filter(edad_minima__lte=self.edad_maxima,
                                                  edad_maxima__gte=self.edad_maxima).exclude(pk=self.pk)
            if categorias.exists():
                raise ValidationError('Ya existe una categoría con el mismo rango de edad.')

    def toJSON(self):
        item = model_to_dict(self)
        item['__str__'] = self.__str__()
        item['rango_edad'] = self.get_rango_edad()
        return item

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        unique_together = ('edad_minima', 'edad_maxima')
        constraints = [
            # Cuota debe ser mayor o igual a 0
            models.CheckConstraint(
                check=models.Q(cuota__gte=0),
                name='cuota_mayor_igual_cero',
                violation_error_message='La cuota debe ser mayor o igual a 0.'
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

    persona = models.ForeignKey('core.Persona', on_delete=models.PROTECT, verbose_name='Persona')
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
            return self.pagocuotasocial_set.exists()
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
        aumento_por_cuota_vencida = Parameters.objects.get(pk=1).aumento_por_cuota_vencida
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
        return self.pagocuotasocial_set.last().fecha_pago.strftime('%d/%m/%Y') if self.is_pagada() else 'Sin pago'

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

    class Meta:
        verbose_name = 'Cuota social'
        verbose_name_plural = 'Cuotas sociales'
        unique_together = ('persona', 'periodo_mes', 'periodo_anio')
        constraints = [
            # Validar que el total sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(total__gte=0),
                                   name='cuota_social_total_valido',
                                   violation_error_message=
                                   'Total: El total debe ser mayor o igual a 0.'),
            # Validar que el cargo extra sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(cargo_extra__gte=0),
                                   name='cuota_social_cargo_extra_valido',
                                   violation_error_message=
                                   'Cargo extra: El cargo extra debe ser mayor o igual a 0.'),
        ]


class ItemCuotaSocial(models.Model):
    """
    Modelo para almacenar los detalles de las cuotas sociales.
    """
    cuota_social = models.ForeignKey('socios.CuotaSocial', on_delete=models.PROTECT, verbose_name='Cuota social')
    socio = models.ForeignKey('socios.Socio', on_delete=models.PROTECT, verbose_name='Socio')
    nombre_completo = models.CharField(max_length=100, verbose_name='Nombre completo')
    categoria = models.CharField(max_length=50, verbose_name='Categoría')
    cuota = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Cuota')
    cargo_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Cargo extra')
    total_parcial = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total parcial',
                                        help_text='Cuota + Cargo extra')
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.nombre_completo} - {self.categoria}'

    def toJSON(self):
        item = model_to_dict(self)
        item['cuota_social'] = self.cuota_social.toJSON()
        item['socio'] = self.socio.toJSON()
        return item

    def save(self, *args, **kwargs):
        self.cuota = self.socio.get_categoria().cuota
        self.total_parcial = self.cuota + self.cargo_extra
        super(ItemCuotaSocial, self).save()

    class Meta:
        verbose_name = 'Detalle de cuota social'
        verbose_name_plural = 'Detalles de cuotas sociales'
        constraints = [
            # Validar que la cuota sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(cuota__gte=0),
                                   name='detalle_cuota_social_cuota_valida',
                                   violation_error_message=
                                   'Cuota: La cuota debe ser mayor o igual a 0.'),
            # Validar que el cargo extra sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(cargo_extra__gte=0),
                                   name='detalle_cuota_social_cargo_extra_valido',
                                   violation_error_message=
                                   'Cargo extra: El cargo extra debe ser mayor o igual a 0.'),
            # Validar que el total parcial sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(total_parcial__gte=0),
                                   name='detalle_cuota_social_total_parcial_valido',
                                   violation_error_message=
                                   'Total parcial: El total parcial debe ser mayor o igual a 0.'),
        ]


class PagoCuotaSocialCuotas(models.Model):
    pago_cuota_social = models.ForeignKey('socios.PagoCuotaSocial', on_delete=models.PROTECT)
    cuota_social = models.ForeignKey('socios.CuotaSocial', on_delete=models.PROTECT)
    interes_aplicado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Interés aplicado')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Subtotal')
    total_pagado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total pagado')

    class Meta:
        db_table = 'socios_pagocuotasocial_cuotas'
        unique_together = ('pago_cuota_social', 'cuota_social')


class PagoCuotaSocial(SoftDeleteModel):
    """
    Modelo para almacenar los pagos de las cuotas sociales.
    """
    cuotas = models.ManyToManyField(
        'socios.CuotaSocial',
        verbose_name='Cuotas sociales',
        through=PagoCuotaSocialCuotas,
        through_fields=('pago_cuota_social', 'cuota_social'),
    )
    medio_pago = models.CharField(max_length=50, verbose_name='Medio de pago')
    fecha_pago = models.DateField(verbose_name='Fecha de pago')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Subtotal')
    interes_aplicado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Interés aplicado')
    total_pagado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total pagado')
    payment_id = models.CharField(max_length=255, verbose_name='Payment ID', unique=True)
    status = models.CharField(max_length=50, verbose_name='Estado')
    status_detail = models.CharField(max_length=255, verbose_name='Detalle del estado')
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')
    date_approved = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de aprobación')
    history = HistoricalRecords()

    def get_STATUS_display(self):
        """Método para mostrar el estado del pago."""
        if self.status == 'approved':
            return 'Aprobado'
        else:
            return 'Pendiente'

    def get_STATUS_DETAIL_display(self):
        """Método para mostrar el detalle del estado del pago."""
        if self.status_detail == 'accredited':
            return 'Acreditado'
        else:
            return 'Pendiente'

    def toJSON(self):
        item = model_to_dict(self)
        item['cuotas'] = [cuota.toJSON() for cuota in self.cuotas.all()]
        return item

    class Meta:
        verbose_name = 'Pago de cuota social'
        verbose_name_plural = 'Pagos de cuotas sociales'
        constraints = [
            # Validar que el total pagado sea mayor o igual a 0.
            models.CheckConstraint(check=models.Q(total_pagado__gte=0),
                                   name='pago_cuota_social_total_pagado_valido',
                                   violation_error_message=
                                   'Total pagado: El total pagado debe ser mayor o igual a 0.'),
        ]
