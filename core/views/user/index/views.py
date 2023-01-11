from django.views.generic import TemplateView

from core.models import Club


class IndexView(TemplateView):
    """Vista para la página de inicio."""
    template_name = 'pages/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inicio'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context
