from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView

from core.models import Cancha


# Vista para obtener canchas disponibles en una fecha y hora.
class CanchasDisponiblesView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista para obtener canchas disponibles en una fecha y hora.
    TODO: Implementar esta vista.
    """
    model = Cancha
    template_name = 'user/reserva/canchas_disponibles.html'
    context_object_name = 'canchas'
    permission_required = 'core.view_reserva'

    def get_queryset(self):
        fecha = self.request.GET.get('fecha')
        hora = self.request.GET.get('hora')
        return Cancha.objects.filter(canchahoralaboral__hora_laboral__hora=hora,
                                     canchahoralaboral__reserva__fecha=fecha,
                                     canchahoralaboral__reserva__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Canchas disponibles'
        return context
