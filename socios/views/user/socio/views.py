from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from core.models import Club
from socios.forms import SocioAdminForm
from socios.mixins import SocioRequiredMixin
from socios.models import Socio


class SocioProfileView(LoginRequiredMixin, SocioRequiredMixin, TemplateView):
    """
    Vista para obtener los datos personales del socio autenticado.
    """
    model = Socio
    form_class = SocioAdminForm
    template_name = 'user/socio/profile.html'

    def get_context_data(self, **kwargs):
        context = super(SocioProfileView, self).get_context_data(**kwargs)
        context['title'] = 'Perfil de Socio'
        context['club_logo'] = Club.objects.get(pk=1).get_imagen()
        context['socio'] = Socio.objects.get(user=self.request.user)
        return context
