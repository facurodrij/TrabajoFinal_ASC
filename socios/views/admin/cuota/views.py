from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView
from django.core.files.storage import FileSystemStorage
from django.template.loader import render_to_string
from weasyprint import HTML, CSS


from accounts.decorators import admin_required
from core.models import Club
from socios.models import CuotaSocial


class CuotaSocialAdminListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """ Vista para listar las cuotas sociales, solo para administradores """
    model = CuotaSocial
    template_name = 'admin/socio/../../../templates/admin/cuota/list.html'
    permission_required = 'socios.view_cuotasocial'
    context_object_name = 'cuotas_sociales'

    def get_queryset(self):
        return CuotaSocial.global_objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cuotas Sociales'
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'mark_as_paid':
                # Si la acción es mark_as_paid, se marca una cuota social como pagada
                cuota_social_id = request.POST['id']
                cuota_social = CuotaSocial.objects.get(pk=cuota_social_id)
                cuota_social.fecha_pago = datetime.now()
                cuota_social.save()
                messages.success(request, 'Cuota social marcada como pagada correctamente')
            else:
                data['error'] = 'Ha ocurrido un error, intente nuevamente'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)


@login_required
@admin_required
def cuota_delete(request, pk):
    """
    Eliminar una cuota social
    """
    cuota = get_object_or_404(CuotaSocial, pk=pk)
    # Obtener el motivo de la eliminación en la url ?motivo=...
    motivo = request.GET.get('motivo', None)
    with transaction.atomic():
        cuota._change_reason = motivo
        cuota.delete(cascade=True)
        messages.success(request, 'Cuota social eliminada correctamente')
    return redirect(request.META.get('HTTP_REFERER'))


@login_required
@admin_required
def cuota_history_pdf(request, cuota_pk, history_pk):
    cuota = CuotaSocial.global_objects.get(pk=cuota_pk)
    club = Club.objects.get(pk=1)
    history = cuota.history.get(pk=history_pk)
    html_string = render_to_string('admin/cuota/history_pdf.html', {'history': history,
                                                                    'cuota': cuota,
                                                                    'club': club})
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    html.write_pdf(target='/tmp/cuota_historial.pdf',
                   stylesheets=[CSS('{}/libs/bootstrap-4.6.2/bootstrap.min.css'.format(settings.STATICFILES_DIRS[0]))])
    fs = FileSystemStorage('/tmp')
    with fs.open('cuota_historial.pdf') as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="cuota_historial.pdf"'
        return response
