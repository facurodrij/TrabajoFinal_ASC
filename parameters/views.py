from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView

from core.models import Club
from parameters.forms import ParametersClubForm
from parameters.models import ClubParameters


class ParametersClubFormView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Vista para la edición de los parámetros de socios."""
    template_name = 'socios.html'
    form_class = ParametersClubForm
    permission_required = 'parameters.change_socios'
    success_url = reverse_lazy('admin-club-parametros')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Parámetros del club'
        return context

    # Definir message success
    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Los parámetros de socios se guardaron correctamente.')
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = ClubParameters.objects.get(club=Club.objects.get(pk=1))
        return kwargs
