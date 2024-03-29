from datetime import datetime

from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from core.models import Club
from eventos.models import Evento
from reservas.forms import ReservaIndexForm


class IndexView(TemplateView):
    """Vista para la página de inicio."""
    template_name = 'pages/user/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inicio'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        context['reserva_form'] = ReservaIndexForm()
        eventos = []
        for e in Evento.objects.filter(fecha_inicio__gte=datetime.now().date()).order_by('fecha_inicio'):
            eventos.append(e) if e.get_start_datetime() > datetime.now() else None
        context['eventos'] = eventos[:5]
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        if request.method == 'POST':
            data['deporte'] = request.POST.get('deporte')
            data['fecha'] = request.POST.get('fecha')
            data['hora'] = request.POST.get('hora')
            return redirect(reverse('reservas-crear') + '?fecha=' + data['fecha'] + '&hora=' + data['hora'] +
                            '&deporte=' + data['deporte'])
