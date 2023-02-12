import uuid
from datetime import timedelta, datetime
from smtplib import SMTPException

from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.forms import model_to_dict
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_softdelete.models import SoftDeleteModel
from simple_history.models import HistoricalRecords

from accounts.models import User
from reservas.tokens import reserva_create_token


class Parameters(models.Model):
    """
    Modelo de los parámetros de las reservas.
    """
    club = models.OneToOneField('core.Club', on_delete=models.CASCADE, verbose_name='Club',
                                related_name='reserva_parameters')
    horas_anticipacion = models.PositiveSmallIntegerField(default=2,
                                                          verbose_name='Horas de anticipación',
                                                          help_text=
                                                          'La fecha de inicio de la reserva debe ser al menos esta'
                                                          ' cantidad de horas mayor a la fecha actual.')
    minutos_expiracion_reserva = models.PositiveSmallIntegerField(default=5,
                                                                  verbose_name='Minutos de expiración por falta de pago',
                                                                  help_text=
                                                                  'La reserva debe ser pagada dentro de esta cantidad de'
                                                                  ' minutos, de lo contrario se cancelará.')
    max_reservas_user = models.PositiveSmallIntegerField(default=2,
                                                         verbose_name='Máximo de reservas activas por usuario',
                                                         help_text=
                                                         'La cantidad máxima de reservas activas que puede tener un'
                                                         ' usuario.')
    avisar_cancha_libre = models.BooleanField(default=True,
                                              verbose_name='Avisar cancha libre',
                                              help_text=
                                              'Enviar avisos a los usuarios sobre la cancha que queda libre,'
                                              ' cuando una reserva que está a pocas horas de comenzar se cancela.')
    horas_avisar_cancha_libre = models.PositiveSmallIntegerField(default=5,
                                                                 verbose_name='Horas para avisar cancha libre',
                                                                 help_text=
                                                                 'Si una reserva se cancela y le quedan menos horas que '
                                                                 'esta cantidad para comenzar, se enviará un aviso a los'
                                                                 ' usuarios.')
    # Campos para definir cuando finaliza una reserva, al comenzar o al terminar.
    finalizar_al_comenzar = models.BooleanField(default=True,
                                                verbose_name='Finalizar al comenzar',
                                                help_text=
                                                'Finalizar la reserva al comenzar, de lo contrario finalizará al'
                                                ' terminar.')
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Parámetro de reserva'
        verbose_name_plural = 'Parámetros de reservas'


class Reserva(SoftDeleteModel):
    """
    Modelo de la reserva.
    """
    FORMA_PAGO = (
        (1, 'Presencial'),
        (2, 'Online'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cancha = models.ForeignKey('reservas.Cancha', on_delete=models.PROTECT)
    nombre = models.CharField(max_length=50, verbose_name='Nombre (cliente)')
    email = models.EmailField(verbose_name='Email (cliente)')
    fecha = models.DateField(verbose_name='Fecha')
    hora = models.TimeField(verbose_name='Hora')
    nota = models.TextField(null=True, blank=True, verbose_name='Nota')
    # Campos para el administrador.
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio')
    con_luz = models.BooleanField(default=False, verbose_name='Con luz', help_text='Marcar si la reserva es con luz')
    expira = models.BooleanField(default=True, verbose_name='Expira (falta de pago)',
                                 help_text='Marcar si expira por falta de pago')
    forma_pago = models.PositiveSmallIntegerField(choices=FORMA_PAGO, default=1, verbose_name='Forma de pago')
    pagado = models.BooleanField(default=False, verbose_name='Pagado', help_text='Marcar si el cliente ya pagó')
    preference_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='Preference ID',
                                     help_text='ID de la preferencia de pago de Mercado Pago')
    asistencia = models.BooleanField(default=False, verbose_name='Asistencia', help_text='Asistencia del cliente')
    # Campos para el historial.
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')
    history = HistoricalRecords()

    def __str__(self):
        return 'Reserva de cancha #{} - {} - {}'.format(self.cancha.id, self.fecha, self.hora)

    def is_finished(self):
        """Método para saber si la reserva ya finalizó."""
        if Parameters.objects.get(club=self.cancha.club).finalizar_al_comenzar:
            return self.start_datetime() < datetime.now().isoformat()
        return self.end_datetime() < datetime.now().isoformat()

    def start_date(self):
        """
        Devuelve la fecha de la reserva en formato yyyy-mm-dd.
        """
        return self.fecha.strftime('%Y-%m-%d')

    def start_datetime(self):
        """Método para obtener la fecha y hora de inicio de la reserva."""
        return datetime.combine(self.fecha, self.hora).isoformat()

    def start_datetime_display(self):
        """Método para obtener la fecha y hora de inicio de la reserva."""
        return datetime.combine(self.fecha, self.hora)

    def end_datetime(self):
        """Método para obtener la fecha y hora de fin de la reserva."""
        return (datetime.combine(self.fecha, self.hora) + timedelta(hours=1)).isoformat()

    def color(self):
        """Método para obtener el color de la reserva."""
        if datetime.combine(self.fecha, self.hora) + timedelta(hours=1) < datetime.now():
            return '#8496a9'
        else:
            return '#0275d8'

    def get_expiration_date(self, isoformat=True):
        """Método para obtener la fecha de expiración de la reserva, en caso de que la forma de pago sea online."""
        minutos = Parameters.objects.get(club=self.cancha.club).minutos_expiracion_reserva
        if self.expira:
            return (self.created_at + timedelta(
                minutes=minutos)).isoformat() if isoformat else self.created_at + timedelta(
                minutes=minutos)
        return None

    def get_FORMA_PAGO_display(self):
        """Método para obtener el nombre de la forma de pago."""
        return dict(self.FORMA_PAGO)[self.forma_pago]

    def get_EXPIRA_display(self):
        """Método para mostrar si la reserva expira por falta de pago."""
        return 'Si' if self.expira else 'No'

    def get_CON_LUZ_display(self):
        """Método para mostrar si la reserva es con luz."""
        return 'Si' if self.con_luz else 'No'

    def get_ESTADO_display(self):
        """Método para mostrar el estado de la reserva."""
        if self.is_finished() and self.asistencia:
            return 'Completada'
        elif self.is_finished() and not self.asistencia:
            return 'Asistencia pendiente'
        elif self.start_datetime() < datetime.now().isoformat():
            return 'En curso'
        else:
            return 'Pendiente'

    def get_ESTADO_PAGO_display(self):
        """Método para mostrar el estado del pago."""
        if self.forma_pago == 1 and self.asistencia:
            return 'Aprobado'
        try:
            pago = PagoReserva.objects.get(reserva=self)
            if pago.status == 'approved':
                return 'Aprobado'
            else:
                return 'Pendiente'
        except PagoReserva.DoesNotExist:
            return 'Pendiente'

    def get_NOTA_display(self):
        """Método para mostrar la nota de la reserva."""
        return self.nota if self.nota else ''

    def send_email(self, subject, template, context):
        """Método para enviar un email."""
        try:
            message = render_to_string(template, context)
            email = EmailMessage(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.email],
            )
            email.content_subtype = 'html'
            email.send()
        except SMTPException as e:
            print('Ha ocurrido un error al enviar el correo electrónico: ', e)
            raise e

    def toJSON(self):
        """Método para convertir la reserva a JSON."""
        item = model_to_dict(self)
        item['deporte'] = self.cancha.deporte.nombre
        item['start'] = self.start_datetime()
        item['end'] = self.end_datetime()
        item['con_luz_display'] = self.get_CON_LUZ_display()
        item['start_display'] = self.start_datetime_display().strftime('%A %d de %B de %Y %H:%M')
        return item

    def clean(self):
        """Método clean() sobrescrito para validar la reserva."""
        super(Reserva, self).clean()
        # Si pasó la fecha de expiración de la reserva y no se ha pagado, se cancela.
        if self.created_at:
            if self.expira and self.get_expiration_date(isoformat=False) < timezone.now() and not self.pagado:
                print('La reserva #{} ha expirado por falta de pago'.format(self.id))
                with transaction.atomic():
                    self.delete()
                raise ValidationError('La {} ha expirado por falta de pago.'.format(self.__str__()),
                                      code='invalid', params={'id': self.id})

    def after_delete(self):
        """Método after_delete() sobrescrito para eliminar la preferencia de pago de Mercado Pago."""
        # TODO: Agregar la opción de descuento.
        horas_avisar_cancha_libre = Parameters.objects.get(pk=1).horas_avisar_cancha_libre
        horas_anticipacion = Parameters.objects.get(pk=1).horas_anticipacion
        if not self.is_finished() and self.pagado and datetime.combine(self.fecha, self.hora) - timedelta(
                hours=horas_avisar_cancha_libre) < datetime.now() + timedelta(hours=horas_anticipacion):
            print('La reserva #{} se ha cancelado a pocas horas de comenzar'.format(self.id))
            with transaction.atomic():
                for user in User.objects.filter(is_active=True, notificaciones=True, is_staff=False,
                                                is_superuser=False).exclude(email=self.email):
                    subject = 'Cancha liberada'
                    template = 'email/cancha_liberada.html'
                    context = {
                        'user': user,
                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                        'token': reserva_create_token.make_token(user),
                        'reserva': self,
                        'protocol': 'http' if settings.DEBUG else 'https',
                        'domain': '127.0.0.1:8000/'
                    }
                    message = render_to_string(template, context)
                    email = EmailMessage(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                    )
                    email.content_subtype = 'html'
                    email.send(fail_silently=True)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = "Reservas"
        constraints = [
            # Validar que no exista una reserva con la misma cancha, fecha, hora y is_deleted=False,
            # pero si con is_deleted=True.
            models.UniqueConstraint(fields=['cancha', 'fecha', 'hora'],
                                    condition=models.Q(is_deleted=False),
                                    name='reserva_unico',
                                    violation_error_message='Ya existe una reserva con la misma cancha, fecha y hora.'),
            # Precio debe ser positivo.
            models.CheckConstraint(check=models.Q(precio__gte=0),
                                   name='precio_positivo',
                                   violation_error_message='El precio debe ser positivo.'),
            # Asistencia no puede ser true si pagado es false.
            models.CheckConstraint(check=~models.Q(asistencia=True, pagado=False),
                                   name='asistencia_pagado',
                                   violation_error_message='No se puede marcar asistencia si la reserva no está'
                                                           ' pagada.'),
        ]


class PagoReserva(models.Model):
    """
    Modelo del pago de la seña de la reserva.
    """
    reserva = models.OneToOneField('reservas.Reserva', on_delete=models.PROTECT, verbose_name='Reserva')
    payment_id = models.CharField(max_length=255, verbose_name='ID de pago')
    status = models.CharField(max_length=50, verbose_name='Estado')
    status_detail = models.CharField(max_length=255, verbose_name='Detalle del estado')
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto de la transacción')
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')
    date_approved = models.DateTimeField(verbose_name='Fecha de aprobación')
    history = HistoricalRecords()

    def __str__(self):
        return 'Pago de reserva #{}'.format(self.reserva.id)

    def toJSON(self):
        """
        Devuelve el modelo en formato JSON.
        """
        item = model_to_dict(self)
        item['reserva'] = self.reserva.toJSON()
        return item

    class Meta:
        verbose_name = 'Pago de reserva'
        verbose_name_plural = "Pagos de reservas"


class Cancha(SoftDeleteModel):
    """
    Modelo de la cancha.
    """
    club = models.ForeignKey('core.Club', on_delete=models.PROTECT)
    superficie = models.ForeignKey('reservas.Superficie', on_delete=models.PROTECT)
    deporte = models.ForeignKey('reservas.Deporte', on_delete=models.PROTECT)
    hora_laboral = models.ManyToManyField('reservas.HoraLaboral',
                                          through='reservas.CanchaHoraLaboral',
                                          through_fields=('cancha', 'hora_laboral'))
    cantidad_jugadores = models.PositiveSmallIntegerField(default=5,
                                                          verbose_name='Cantidad de jugadores',
                                                          help_text='Cantidad de jugadores por equipo',
                                                          validators=[MinValueValidator(1), MaxValueValidator(20)],
                                                          null=True, blank=True)
    precio = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Precio por hora')
    precio_luz = models.DecimalField(max_digits=6,
                                     decimal_places=2,
                                     null=True, blank=True,
                                     verbose_name='Precio por hora con luz')
    history = HistoricalRecords()

    def imagen_directory_path(self, filename):
        """Método para obtener la ruta de la imagen de la cancha."""
        return 'img/cancha/{0}/{1}'.format(self.id, filename)

    imagen = models.ImageField(upload_to=imagen_directory_path, null=True, blank=True, verbose_name='Imagen')

    def __str__(self):
        return 'Cancha #{}'.format(self.id)

    def save(self, *args, **kwargs):
        """Método save() sobrescrito para redimensionar la imagen."""
        super().save(*args, **kwargs)

        try:
            img = Image.open(self.imagen.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.imagen.path)
        except (FileNotFoundError, ValueError):
            pass

    def get_imagen(self):
        """Método para obtener la imagen de perfil del usuario."""
        try:
            # Si existe una imagen en self.imagen.url, la devuelve.
            Image.open(self.imagen.path)
            return self.imagen.url
        except FileNotFoundError:
            return settings.STATIC_URL + 'img/empty.svg'

    class Meta:
        verbose_name = 'Cancha'
        verbose_name_plural = "Canchas"
        ordering = ['id']
        constraints = [
            # El precio por hora con luz no puede ser menor al precio por hora.
            models.CheckConstraint(check=models.Q(precio_luz__gte=models.F('precio')),
                                   name='precio_luz_mayor_precio',
                                   violation_error_message='El precio por hora con luz no '
                                                           'puede ser menor al precio por hora.')
        ]

    def is_available(self, fecha, hora_inicio):
        """Método para verificar si la cancha está disponible en una fecha y hora determinada."""
        # Se obtiene la hora laboral de la cancha.
        hora_laboral = self.hora_laboral.filter(hora=hora_inicio)

        # Si no existe una hora laboral para la fecha, la cancha no está disponible.
        if not hora_laboral:
            return False

        # Se obtienen las reservas de la cancha para la fecha y hora.
        try:
            reserva = self.reserva_set.get(fecha=fecha, hora=hora_inicio, is_deleted=False)
            reserva.clean()
        except (Reserva.DoesNotExist, ValidationError):
            return True

        if reserva:
            return False


class CanchaHoraLaboral(models.Model):
    """
    Modelo del horario de la cancha.
    """
    cancha = models.ForeignKey('reservas.Cancha', on_delete=models.PROTECT)
    hora_laboral = models.ForeignKey('reservas.HoraLaboral', on_delete=models.PROTECT)
    con_luz = models.BooleanField(default=False, verbose_name='Con luz')

    def __str__(self):
        return 'Cancha #{} - {}'.format(self.cancha.id, self.hora_laboral)

    class Meta:
        unique_together = ('cancha', 'hora_laboral')
        verbose_name = 'Horario de cancha'
        verbose_name_plural = "Horarios de canchas"


class HoraLaboral(models.Model):
    """
    Modelo de la hora laboral.
    """
    club = models.ForeignKey('core.Club', on_delete=models.PROTECT)
    hora = models.TimeField(verbose_name='Hora')

    def __str__(self):
        return str(self.hora)

    class Meta:
        unique_together = ('club', 'hora')
        verbose_name = 'Hora laboral'
        verbose_name_plural = "Horas laborales"
        ordering = ['hora']


class Deporte(models.Model):
    """Modelo para almacenar los deportes."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Deporte'
        verbose_name_plural = 'Deportes'


class Superficie(models.Model):
    """Modelo para almacenar las superficies."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Superficie'
        verbose_name_plural = 'Superficies'
