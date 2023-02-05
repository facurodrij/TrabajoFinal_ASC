from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import TemplateView

from config.mixins import AdminRequiredMixin
from reservas.models import Reserva, HoraLaboral


class EstadisticaAdminView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'admin/estadistica.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Estadísticas'
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        start_date = request.POST.get('start')
        end_date = request.POST.get('end')
        report = request.POST.get('report')
        if report == 'reserva':
            # Obtener la recaudación de las reservas por horario laboral en el rango de fechas seleccionado
            data = []
            for hora in HoraLaboral.objects.all():
                hora = hora.hora.strftime('%H:%M:%S')
                reservas = Reserva.objects.filter(fecha__range=[start_date, end_date], hora=hora, pagado=True)
                total = 0
                for reserva in reservas:
                    total += reserva.precio
                data.append({
                    'hora': hora,
                    'total': total,
                })
        return JsonResponse(data, safe=False)
