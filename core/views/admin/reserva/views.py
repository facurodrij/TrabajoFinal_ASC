from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView

from core.forms import ReservaAdminForm
from core.models import Reserva, Cancha


class ReservaAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar las reservas.
    TODO: Implementar esta vista.
    """
    model = Reserva
    template_name = 'admin/reserva/list.html'
    context_object_name = 'reservas'
    permission_required = 'core.view_reserva'

    def get_queryset(self):
        return Reserva.objects.all().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Reservas'
        return context


class ReservaAdminCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Vista para crear una reserva.
    """
    model = Reserva
    template_name = 'admin/reserva/form.html'
    form_class = ReservaAdminForm
    permission_required = 'core.add_reserva'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear reserva'
        context['action'] = 'add'
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                form = self.form_class(request.POST)
                if form.is_valid():
                    with transaction.atomic():
                        # Obtener la hora
                        hora = form.cleaned_data['hora']
                        reserva = form.save(commit=False)
                        reserva.hora = hora.hora
                        con_luz = hora.canchahoralaboral_set.first().con_luz
                        reserva.con_luz = con_luz
                        reserva.save()
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = e.args[0]
        print('ReservaAdminCreateView: ', data)
        return JsonResponse(data)


class ReservaAdminUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para actualizar una reserva.
    TODO: Crear reestricción que no permita editar una reserva que ya fue jugada o pasado 1 día de crearla.
    """
    model = Reserva
    template_name = 'admin/reserva/form.html'
    form_class = ReservaAdminForm
    permission_required = 'core.change_reserva'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Reserva'
        context['action'] = 'edit'
        return context


def reserva_admin_ajax(request):
    data = {}
    # Obtener si el GET o POST
    if request.method == 'GET':
        action = request.GET['action']
        if action == 'get_canchas_disponibles':
            hora = request.GET['hora']
            fecha = request.GET['fecha']
            try:
                # Excluir las canchas que tengan reservas en esa hora y fecha y no esten eliminadas
                canchas_disp = Cancha.objects.all()
                for reserva in Reserva.objects.filter(hora=hora, fecha=fecha, is_deleted=False):
                    canchas_disp = canchas_disp.exclude(id=reserva.cancha.id)
                if canchas_disp:
                    print(canchas_disp)
                    data['canchas'] = list(canchas_disp.values_list('id'))
                else:
                    data['error'] = 'No hay canchas disponibles para la fecha y hora seleccionada.'
            except Exception as e:
                data['error'] = e.args[0]
    elif request.method == 'POST':
        pass
    print('socio_admin_ajax: ', data)
    return JsonResponse(data, safe=False)
