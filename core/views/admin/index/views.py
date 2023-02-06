from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from config.mixins import AdminRequiredMixin
from core.models import Club


class IndexAdminView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Vista para la página de inicio de administración."""
    template_name = 'pages/admin/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inicio'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        return context
