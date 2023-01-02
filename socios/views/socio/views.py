from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, TemplateView

from core.models import Club
from socios.forms import SocioAdminForm
from socios.mixins import SocioRequiredMixin
from socios.models import Socio


class SocioUserView(LoginRequiredMixin, TemplateView):
    """
    Vista para obtener los datos personales del socio autenticado.
    """
    model = Socio
    form_class = SocioAdminForm
    template_name = 'socio/user.html'

    def get_context_data(self, **kwargs):
        context = super(SocioUserView, self).get_context_data(**kwargs)
        context['title'] = 'Perfil de Socio'
        context['socio'] = Socio.objects.get(user=self.request.user)
        return context
