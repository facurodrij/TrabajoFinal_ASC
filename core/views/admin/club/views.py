from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView

from config.mixins import AdminRequiredMixin
from core.forms import *
from core.models import Club


class ClubFormView(LoginRequiredMixin, AdminRequiredMixin, FormView):
    """ Vista para el club, solo acceden superusuarios, staff y administradores del club """
    template_name = 'admin/club.html'
    form_class = ClubForm
    success_url = reverse_lazy('admin-club-form')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mi Club'
        context['object'] = Club.objects.get(pk=1)
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Club actualizado exitosamente')
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Club.objects.get(pk=1)
        return kwargs
