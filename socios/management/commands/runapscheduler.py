import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import make_aware
from django_apscheduler import util
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

from parameters.models import Socios
from socios.models import Socio, CuotaSocial, DetalleCuotaSocial

logger = logging.getLogger(__name__)


def add_cuota_social():
    """
    Este método genera una cuota social a cada socio titular
    """
    print('Procesando Job add_cuota_social()..')
    dia_emision_cuota = Socios.objects.get(club_id=1).dia_emision_cuota
    # Los dia_emision_cuota de cada mes se ejecuta el proceso automatizado
    if datetime.now().day == dia_emision_cuota and datetime.now().hour == 0 and datetime.now().minute == 0:
        # Por cada Socio que es_titular sea verdadero
        with transaction.atomic():
            for socio in Socio.objects.filter(socio_titular__isnull=True):
                print('Procesando Socio: ', socio, ' - ', socio.get_tipo())
                # Fecha de vencimiento, 1 mes después de la fecha de emisión
                cuota_social = CuotaSocial(persona=socio.persona,
                                           fecha_emision=make_aware(datetime.now()),
                                           # Fecha de vencimiento, 21 días después de la fecha de emisión
                                           fecha_vencimiento=make_aware(datetime.now() + relativedelta(days=21)))
                cuota_social.save()
                # Agregar el detalle de la cuota social
                detalle = DetalleCuotaSocial()
                detalle.cuota_social = cuota_social
                detalle.socio = cuota_social.persona.socio
                detalle.save()
                for miembro in cuota_social.persona.socio.get_miembros():
                    detalle_miembro = DetalleCuotaSocial()
                    detalle_miembro.cuota_social = cuota_social
                    detalle_miembro.socio = miembro
                    detalle_miembro.save()
                # Generar el total, sumando los totales parciales de los detalles relacionados.
                total = cuota_social.cargo_extra
                for detalle in cuota_social.detallecuotasocial_set.all():
                    total += detalle.total_parcial
                cuota_social.total = total
                cuota_social.save()
            print('Cuotas sociales agregadas a cada socio titular')


def delete_socio_moroso():
    """
    Este método elimina a los socios que tengan una mayor cantidad pendiente de cuotas sociales,
    de acuerdo a la cantidad establecida por el club
    """
    print('Procesando Job delete_socio_moroso()..')
    # Los 6 de cada mes a las 23:59 se ejecuta el proceso automatizado
    if datetime.now().day == 6 and datetime.now().hour == 23 and datetime.now().minute == 59:
        # Por cada Socio que es_titular sea verdadero
        with transaction.atomic():
            for socio in Socio.objects.filter(socio_titular__isnull=True):
                print('Procesando Socio: ', socio, ' - ', socio.get_tipo())
                # Obtener la cantidad de cuotas sociales pendientes
                cuotas_pendientes = CuotaSocial.objects.filter(persona=socio.persona, fecha_pago__isnull=True).count()
                # Si la cantidad de cuotas pendientes es mayor a 2, eliminar al socio en cascada
                if cuotas_pendientes > 2:
                    socio.delete(cascade=True)
                    print('Socio {} eliminado por morosidad'.format(socio))
            print('Socios morosos eliminados')


# The `close_old_connections` decorator ensures that database connections, that have become
# unusable or are obsolete, are closed before and after your job has run. You should use it
# to wrap any jobs that you schedule that access the Django database in any way.
@util.close_old_connections
def delete_old_job_executions(max_age=604_800):
    """
    This job deletes APScheduler job execution entries older than `max_age` from the database.
    It helps to prevent the database from filling up with old historical records that are no
    longer useful.

    :param max_age: The maximum length of time to retain historical job execution records.
                    Defaults to 7 days.
    """
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs APScheduler."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            add_cuota_social,
            trigger=CronTrigger(minute="*/1"),  # Run each 1 minute
            id="add_cuota_social",  # The `id` assigned to each job MUST be unique
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job 'my_job'.")

        scheduler.add_job(
            delete_socio_moroso,
            trigger=CronTrigger(minute="*/1"),  # Run each 1 minute
            id="delete_socio_moroso",  # The `id` assigned to each job MUST be unique
            max_instances=1,
            replace_existing=True,
        )

        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(
                day_of_week="mon", hour="00", minute="00"
            ),  # Midnight on Monday, before start of the next work week.
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
        )
        logger.info(
            "Added weekly job: 'delete_old_job_executions'."
        )

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")
