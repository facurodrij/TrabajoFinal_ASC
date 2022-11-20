from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import FormView
from django.views.generic.list import ListView

from core.models import Club
from socios.forms import SocioForm
from socios.models import Socio, CuotaSocial
from socios.mixins import SocioRequiredMixin


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


class CuotaSocialListView(LoginRequiredMixin, SocioRequiredMixin, ListView):
    """
    Vista para obtener el listado de cuotas sociales del socio logueado
    """
    model = CuotaSocial
    template_name = 'socio/cuota_list.html'
    context_object_name = 'cuotas_sociales'

    def get_context_data(self, **kwargs):
        context = super(CuotaSocialListView, self).get_context_data(**kwargs)
        context['title'] = 'Mis Cuotas'
        return context

    def get_queryset(self):
        return CuotaSocial.objects.filter(detallecuotasocial__socio=self.request.user.persona.socio)
