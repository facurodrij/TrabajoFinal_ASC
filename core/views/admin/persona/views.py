from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView

from core.forms import PersonaAdminForm
from core.models import Persona


class PersonaAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para el listado de personas """
    model = Persona
    template_name = 'admin/persona/list.html'
    permission_required = 'accounts.view_persona'
    context_object_name = 'personas'

    def get_queryset(self):
        return Persona.global_objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Personas'
        return context


class PersonaAdminCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """ Vista para la creación de personas """
    model = Persona
    form_class = PersonaAdminForm
    template_name = 'admin/persona/form.html'
    permission_required = 'accounts.add_persona'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva Persona'
        if self.request.GET.get('titular'):
            context['title'] = 'Nuevo Persona Titular'
        context['action'] = 'add'
        return context

    # Si en la url existe 'titular=true', se deshabilita el campo es_menor del formulario
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.GET.get('titular'):
            form.fields['es_menor'].widget.attrs['disabled'] = True
            form.fields['persona_titular'].widget.attrs['disabled'] = True
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                form = self.form_class(request.POST, request.FILES)
                if form.is_valid():
                    with transaction.atomic():
                        persona = form.save()
                        persona_titular = form.cleaned_data.get('persona_titular')
                        if persona_titular:
                            persona.persona_titular = persona_titular
                            persona.save()
                        data['persona'] = persona.toJSON()
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = e.args[0]
        print(data)
        return JsonResponse(data)


class PersonaAdminUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """ Vista para la actualización de personas """
    model = Persona
    form_class = PersonaAdminForm
    template_name = 'admin/persona/form.html'
    permission_required = 'accounts.change_persona'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Persona'
        context['action'] = 'edit'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['persona_titular'].initial = self.object.persona_titular
        form.fields['persona_titular'].queryset = Persona.objects.filter(persona_titular__isnull=True).exclude(
            pk=self.object.pk)
        if self.object.persona_set.exists():
            form.fields['persona_titular'].widget.attrs['disabled'] = True
            form.fields['persona_titular'].help_text = 'No se puede modificar porque la persona tiene personas a cargo.'
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            change_reason = request.POST['change_reason']
            if action == 'edit':
                form = self.form_class(request.POST, request.FILES, instance=self.get_object())
                if form.is_valid():
                    with transaction.atomic():
                        persona_titular = form.cleaned_data.get('persona_titular')
                        if persona_titular:
                            persona = form.save(commit=False)
                            persona.persona_titular = persona_titular
                            persona._change_reason = change_reason
                            persona.save()
                        else:
                            persona = form.save(commit=False)
                            persona.persona_titular = None
                            persona._change_reason = change_reason
                            persona.save()
                        messages.success(request, 'Persona actualizada correctamente.')
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = e.args[0]
        print(data)
        return JsonResponse(data)

# TODO: PersonaAdminDetailView
# TODO: PersonaAdminDeleteView
