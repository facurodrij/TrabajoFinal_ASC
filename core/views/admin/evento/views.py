from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.http import JsonResponse, HttpResponseRedirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages

from core.models import Evento, TicketVariante
from core.forms import EventoForm, TicketVarianteFormSet


class EventoAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Evento
    template_name = 'admin/evento/list.html'
    context_object_name = 'eventos'
    permission_required = 'core.view_evento'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Eventos'
        return context


class EventoInline:
    form_class = EventoForm
    model = Evento
    template_name = 'admin/evento/form.html'

    def form_valid(self, form):
        named_formsets = self.get_named_formsets()
        if not all((x.is_valid() for x in named_formsets.values())):
            return self.render_to_response(self.get_context_data(form=form))

        self.object = form.save()

        # for every formset, attempt to find a specific formset save function
        # otherwise, just save.
        for name, formset in named_formsets.items():
            formset_save_func = getattr(self, 'formset_{0}_valid'.format(name), None)
            if formset_save_func is not None:
                formset_save_func(formset)
            else:
                formset.save()
        messages.success(self.request, 'Evento guardado correctamente')
        return redirect('admin-eventos-listado')

    def formset_ticketvariante_valid(self, formset):
        """
        Hook for custom formset saving.Useful if you have multiple formsets
        """
        variants = formset.save(commit=False)  # self.save_formset(formset, contact)
        # add this 2 lines, if you have can_delete=True parameter
        # set in inlineformset_factory func
        for obj in formset.deleted_objects:
            obj.delete()
        for variant in variants:
            variant.evento = self.object
            variant.save()


class EventoAdminCreateView(LoginRequiredMixin, PermissionRequiredMixin, EventoInline, CreateView):
    permission_required = 'core.add_evento'
    success_url = reverse_lazy('admin-eventos-listado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Evento'
        context['named_formsets'] = self.get_named_formsets()
        context['action'] = 'add'
        return context

    def get_named_formsets(self):
        if self.request.method == "GET":
            return {'ticketvariante': TicketVarianteFormSet(prefix='ticketvariante')}
        else:
            return {'ticketvariante': TicketVarianteFormSet(self.request.POST or None, prefix='ticketvariante')}


class EventoAdminUpdateView(LoginRequiredMixin, PermissionRequiredMixin, EventoInline, UpdateView):
    permission_required = 'core.change_evento'
    success_url = reverse_lazy('admin-eventos-listado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Evento'
        context['named_formsets'] = self.get_named_formsets()
        context['action'] = 'edit'
        return context

    def get_named_formsets(self):
        if self.request.method == "GET":
            return {'ticketvariante': TicketVarianteFormSet(instance=self.object, prefix='ticketvariante')}
        else:
            return {'ticketvariante': TicketVarianteFormSet(self.request.POST or None, instance=self.object,
                                                            prefix='ticketvariante')}


class EventoAdminDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Evento
    template_name = 'admin/evento/delete.html'
    context_object_name = 'evento'
    permission_required = 'core.delete_evento'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Baja de Evento'
        return context

    def post(self, request, *args, **kwargs):
        evento = self.get_object()
        with transaction.atomic():
            TicketVariante.objects.filter(evento=evento).delete()
            evento.delete()
            messages.success(request, 'Evento dado de baja correctamente')
        return redirect('admin-eventos-listado')
