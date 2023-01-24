from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView

from core.forms import ReservaAdminForm
from core.models import Reserva, Cancha, PagoReserva
from parameters.models import ReservaParameters


class ReservaAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar las reservas.
    TODO: Mostrar referencia de colores.
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
        context['title'] = 'Crear Reserva'
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
                        form.save()
                        # TODO: Enviar correo con el link de pago.
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = e.args[0]
        print('ReservaAdminCreateView: ', data)
        return JsonResponse(data, safe=False)


class ReservaAdminDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Vista para mostrar los detalles de una reserva.
    """
    model = Reserva
    template_name = 'admin/reserva/detail.html'
    context_object_name = 'reserva'
    permission_required = 'core.view_reserva'

    def dispatch(self, request, *args, **kwargs):
        reserva = self.get_object()
        try:
            reserva.clean()
        except ValidationError as e:
            messages.error(request, e.args[0])
            return redirect('admin-reservas-listado')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Detalle de Reserva'
        if self.object.forma_pago == 2:
            try:
                context['pago'] = self.object.pagoreserva
            except PagoReserva.DoesNotExist:
                pass
        return context


class ReservaAdminUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para actualizar una reserva.
    """
    model = Reserva
    template_name = 'admin/reserva/form.html'
    form_class = ReservaAdminForm
    permission_required = 'core.change_reserva'

    def dispatch(self, request, *args, **kwargs):
        reserva = self.get_object()
        # Si la reserva tiene como método de pago online, no se puede editar.
        if reserva.forma_pago == 2:
            messages.error(request, 'No se puede editar una reserva que tiene forma de pago online.')
            return redirect('admin-reservas-detalle', pk=reserva.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Reserva'
        context['action'] = 'edit'
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                form = self.form_class(request.POST, instance=self.get_object())
                if form.is_valid():
                    with transaction.atomic():
                        form.save()
                        # TODO: Enviar correo con aviso de cambio de reserva.
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = e.args[0]
        print('ReservaAdminUpdateView: ', data)
        return JsonResponse(data, safe=False)


class ReservaAdminDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Vista para eliminar un socio, solo para administradores
    """
    model = Reserva
    template_name = 'admin/reserva/delete.html'
    permission_required = 'reservas.delete_reserva'
    context_object_name = 'reserva'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Baja de Reserva'
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            with transaction.atomic():
                reserva = self.get_object()
                reserva.delete()
                messages.success(request, 'Reserva dada de baja exitosamente.')
                # TODO: Ejecutar proceso automatizado de enviar avisos sobre la cancelación de la reserva.
                # TODO: Enviar aviso sobre la cancelación de la reserva.
        except Exception as e:
            data['error'] = e.args[0]
        print('ReservaAdminDeleteView: ', data)
        return redirect('admin-reservas-listado')


def reserva_admin_ajax(request):
    data = {}
    # Obtener si el GET o POST
    try:
        if request.method == 'GET':
            action = request.GET['action']
            if action == 'get_canchas_disponibles':
                deporte_id = request.GET['deporte_id']
                hora = request.GET['hora']
                fecha = request.GET['fecha']
                fecha = datetime.strptime(fecha, '%Y-%m-%d')
                hora = datetime.strptime(hora, '%H:%M:%S')
                start_date = datetime.combine(fecha, hora.time())
                # Fecha de inicio de la reserva debe ser con al menos 2 horas de anticipación
                # Si el usuario no es anónimo, se le permite reservar con 2 hora de anticipación.
                cant_horas = ReservaParameters.objects.get(club_id=1).horas_anticipacion
                if request.user.is_anonymous:
                    if start_date < datetime.now() + timedelta(hours=cant_horas):
                        data['error'] = 'El inicio de la reserva debe ser con al menos {} horas de ' \
                                        'anticipación.'.format(cant_horas)
                        return JsonResponse(data, safe=False)
                elif not request.user.is_admin():
                    if start_date < datetime.now() + timedelta(hours=cant_horas):
                        data['error'] = 'El inicio de la reserva debe ser con al menos {} horas de ' \
                                        'anticipación.'.format(cant_horas)
                        return JsonResponse(data, safe=False)
                # Excluir las canchas que tengan reservas en esa hora y fecha y no estén eliminadas
                canchas_disp = Cancha.objects.filter(deporte_id=deporte_id, hora_laboral__hora=hora.time())
                for reserva in Reserva.objects.filter(cancha__deporte_id=deporte_id,
                                                      hora=hora,
                                                      fecha=fecha,
                                                      is_deleted=False):
                    try:
                        reserva.clean()
                        canchas_disp = canchas_disp.exclude(id=reserva.cancha.id)
                    except ValidationError:
                        pass
                if canchas_disp:
                    data['canchas'] = list(canchas_disp.values_list('id'))
                else:
                    data['error'] = 'No hay canchas disponibles para la fecha y hora seleccionada.'
        elif request.method == 'POST':
            action = request.POST['action']
            if action == 'check_asistencia':
                reserva_id = request.POST['reserva_id']
                reserva = Reserva.objects.get(pk=reserva_id)
                if reserva.is_finished():
                    if not reserva.asistencia and reserva.forma_pago == 1:
                        reserva.pagado = True
                        reserva.asistencia = True
                        reserva.save()
                    elif not reserva.asistencia and reserva.forma_pago == 2:
                        reserva.asistencia = True
                        reserva.save()
                    else:
                        data['error'] = 'La asistencia ya fue registrada.'
                else:
                    data['error'] = 'No se puede registrar la asistencia de una reserva que no haya finalizado.'
    except Exception as e:
        data['error'] = e.args[0]
    print('socio_admin_ajax: ', data)
    return JsonResponse(data, safe=False)
