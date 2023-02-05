from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from config.mixins import AdminRequiredMixin


class EstadisticaAdminView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    pass
