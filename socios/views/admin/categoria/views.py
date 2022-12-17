from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView

from socios.forms import CategoriaForm
from socios.models import Categoria


class CategoriaAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para listar las categorias, solo para administradores """
    model = Categoria
    template_name = 'admin/categoria/list.html'
    permission_required = 'socios.view_categoria'
    context_object_name = 'categorias'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Categorias de Socios'
        return context


class CategoriaAdminCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """ Vista para crear una categoria, solo para administradores """
    model = Categoria
    form_class = CategoriaForm
    template_name = 'admin/categoria/form.html'
    permission_required = 'socios.add_categoria'
    success_url = reverse_lazy('admin-categoria-listado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva Categoria'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'La categoria se guardó correctamente.')
        return super().form_valid(form)


class CategoriaAdminUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """ Vista para crear una categoria, solo para administradores """
    model = Categoria
    form_class = CategoriaForm
    template_name = 'admin/categoria/form.html'
    permission_required = 'socios.change_categoria'
    success_url = reverse_lazy('admin-categoria-listado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Categoria'
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'La categoria se actualizó correctamente.')
        return super().form_valid(form)
