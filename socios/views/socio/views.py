from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import FormView

from core.models import Club
from socios.forms import SocioTitularForm
from socios.models import Socio


class SocioFormView(LoginRequiredMixin, FormView):
    model = Socio
    form_class = SocioTitularForm
    template_name = 'socio/form.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_admin():
            return redirect('socio-listado')
        if request.user.persona.get_socio() is None:
            messages.error(request, 'No tiene permisos para acceder a esta página.')
            return redirect('index')
        return super(SocioFormView, self).dispatch(request, *args, **kwargs)

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
