from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from config.mixins import AdminRequiredMixin
from core.models import Club
from eventos.models import Ticket
from reservas.models import Reserva
from socios.models import Socio, CuotaSocial


class IndexAdminView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Vista para la página de inicio de administración."""
    template_name = 'pages/admin/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Dashboard Administración'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        context['socios_activos'] = Socio.objects.all().count()
        context['reservas_activas'] = Reserva.objects.all().count()
        context['tickets_vendidos'] = Ticket.objects.all().count()
        context['cuotas_sociales_pendientes'] = CuotaSocial.objects.filter(pagocuotasocial__isnull=True).count()
        return context
