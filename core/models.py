import uuid
from datetime import timedelta, datetime
from smtplib import SMTPException

from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.forms import model_to_dict
from django.template.loader import render_to_string
from django.utils import timezone
from django_softdelete.models import SoftDeleteModel
from simple_history.models import HistoricalRecords

from parameters.models import ReservaParameters
from accounts.models import User


class Club(SoftDeleteModel):
    """
    Modelo del club.
    """
    localidad = models.ForeignKey('parameters.Localidad', on_delete=models.PROTECT)
    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    direccion = models.CharField(max_length=255, verbose_name='Dirección')
    email = models.EmailField(max_length=255, verbose_name='Email')

    def imagen_directory_path(self, filename):
        """Método para obtener la ruta de la imagen del logo del club."""
        return 'img/club/{0}/{1}'.format(self.id, filename)

    imagen = models.ImageField(upload_to=imagen_directory_path, null=True, blank=True, verbose_name='Logo')

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        """Método save() sobrescrito para redimensionar la imagen."""
        super().save(*args, **kwargs)
        try:
            img = Image.open(self.imagen.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.imagen.path)
        except FileNotFoundError:
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
        unique_together = ('localidad', 'direccion')
        verbose_name = 'Club'
        verbose_name_plural = "Clubes"
        ordering = ['id']


class Cancha(SoftDeleteModel):
    """
    Modelo de la cancha.
    """
    club = models.ForeignKey(Club, on_delete=models.PROTECT)
    superficie = models.ForeignKey('parameters.Superficie', on_delete=models.PROTECT)
    deporte = models.ForeignKey('parameters.Deporte', on_delete=models.PROTECT)
    hora_laboral = models.ManyToManyField('HoraLaboral',
                                          through='CanchaHoraLaboral',
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


class CanchaHoraLaboral(models.Model):
    """
    Modelo del horario de la cancha.
    """
    cancha = models.ForeignKey('Cancha', on_delete=models.PROTECT)
    hora_laboral = models.ForeignKey('HoraLaboral', on_delete=models.PROTECT)
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
    club = models.ForeignKey(Club, on_delete=models.PROTECT)
    hora = models.TimeField(verbose_name='Hora')

    def __str__(self):
        return str(self.hora)

    class Meta:
        unique_together = ('club', 'hora')
        verbose_name = 'Hora laboral'
        verbose_name_plural = "Horas laborales"
        ordering = ['hora']


class Reserva(SoftDeleteModel):
    """
    Modelo de la reserva.
    """
    FORMA_PAGO = (
        (1, 'Presencial'),
        (2, 'Online'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cancha = models.ForeignKey('Cancha', on_delete=models.PROTECT)
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
        if ReservaParameters.objects.get(club=self.cancha.club).finalizar_al_comenzar:
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
        minutos = ReservaParameters.objects.get(club=self.cancha.club).minutos_expiracion
        if self.expira:
            if isoformat:
                return (self.created_at + timedelta(minutes=minutos)).isoformat()
            return self.created_at + timedelta(minutes=minutos)
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
        if self.is_paid():
            if self.is_finished():
                return 'Finalizada'
            else:
                return 'Activa'
        elif self.is_finished():
            return 'Expirada'
        return 'Pendiente de pago'

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
        return item

    def clean(self):
        """Método clean() sobrescrito para validar la reserva."""
        super(Reserva, self).clean()
        # Si pasó la fecha de expiración de la reserva y no se ha pagado, se cancela.
        if self.created_at:
            if self.expira and self.get_expiration_date(isoformat=False) < timezone.now() and not self.pagado:
                print('La reserva #{} ha expirado por falta de pago'.format(self.id))
                self.delete()
                raise ValidationError('La reserva #{} ha expirado por falta de pago.'.format(self.id),
                                      code='invalid', params={'id': self.id})

    def after_delete(self):
        """Método after_delete() sobrescrito para eliminar la preferencia de pago de Mercado Pago."""
        # TODO: Eliminar la preferencia de pago de Mercado Pago.
        # TODO: Enviar avisos a los usuarios sobre la cancha que queda libre.
        #  Cuando la reserva está a pocas horas de comenzar. (Parametrizar la cantidad de horas)
        # TODO: Ejecutar proceso automatizado de enviar avisos sobre la cancelación de la reserva.
        #  Revisar si la reserva se canceló dentro del plazo necesario para que se ejecutara el proceso
        #  Filtrar por los usuarios que tienen la opción de recibir avisos de cancelación de reservas.
        #  Teniendo esos usuarios, enviarles un correo con el aviso de la liberación de la cancha en
        #  el horario de la reserva cancelada y la opción de reservarla nuevamente con un descuento.
        horas_avisar_cancha_libre = ReservaParameters.objects.get(pk=1).horas_avisar_cancha_libre
        horas_anticipacion = ReservaParameters.objects.get(pk=1).horas_anticipacion
        if not self.is_finished() and datetime.combine(self.fecha, self.hora) - timedelta(
                hours=horas_avisar_cancha_libre) < datetime.now() + timedelta(hours=horas_anticipacion):
            print('La reserva #{} se ha cancelado a pocas horas de comenzar'.format(self.id))
            for user in User.objects.filter(is_active=True, notificaciones=True, is_staff=False, is_superuser=False):
                subject = 'Cancha liberada'
                template = 'email/cancha_liberada.html'
                context = {
                    'cancha': self.cancha,
                    'fecha': self.fecha,
                    'hora': self.hora,
                    'precio': self.precio,
                    'email': user.email,
                    'nombre': user.nombre,
                }
                try:
                    message = render_to_string(template, context)
                    email = EmailMessage(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                    )
                    email.content_subtype = 'html'
                    email.send()
                except SMTPException as e:
                    print('Ha ocurrido un error al enviar el correo electrónico: ', e)
                    raise e

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
    payment_id = models.CharField(max_length=255, verbose_name='ID de pago')
    reserva = models.OneToOneField('Reserva', on_delete=models.PROTECT, verbose_name='Reserva')
    preference_id = models.CharField(max_length=255, verbose_name='ID de preferencia')
    date_created = models.DateTimeField(verbose_name='Fecha de creación')
    date_approved = models.DateTimeField(verbose_name='Fecha de aprobación')
    date_last_updated = models.DateTimeField(verbose_name='Fecha de última actualización')
    payment_method_id = models.CharField(max_length=50, verbose_name='Método de pago')
    payment_type_id = models.CharField(max_length=50, verbose_name='Tipo de pago')
    status = models.CharField(max_length=50, verbose_name='Estado')
    status_detail = models.CharField(max_length=255, verbose_name='Detalle del estado')
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto de la transacción')

    def __str__(self):
        return 'Pago de reserva #{}'.format(self.reserva.id)

    def send_email(self, subject, template, context):
        """Método para enviar un email."""
        try:
            message = render_to_string(template, context)
            email = EmailMessage(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.reserva.email],
            )
            email.content_subtype = 'html'
            email.send()
        except SMTPException as e:
            print('Ha ocurrido un error al enviar el correo electrónico: ', e)
            raise e

    class Meta:
        verbose_name = 'Pago de reserva'
        verbose_name_plural = "Pagos de reservas"
