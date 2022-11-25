from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView

from core.models import Club
from socios.forms import SocioForm
from socios.mixins import SocioRequiredMixin
from socios.models import Socio


class SocioFormView(LoginRequiredMixin, SocioRequiredMixin, FormView):
    """
    Vista para obtener los datos del socio logueado
    """
    model = Socio
    form_class = SocioForm
    template_name = 'socio/info.html'

    # Obtener la categoria del socio
    def get_initial(self):
        socio = self.request.user.persona.get_socio()
        return {
            'categoria': socio.categoria,
        }

    def get_context_data(self, **kwargs):
        context = super(SocioFormView, self).get_context_data(**kwargs)
        context['title'] = 'Información del socio'
        context['club'] = Club.objects.get(pk=1)
        return context
