from django.urls import path

from socios.views.admin.cuota.views import *
from socios.views.admin.socio.views import *
from socios.views.cuota.views import *
from socios.views.socio.views import *
from socios.views.solicitud.views import *

urlpatterns = [
    # # URLs de socios (administración)
    # Si ingresan a admin/socios/ se redirige a admin-socio-listado
    path('admin/socios/', lambda request: redirect('admin-socio-listado', permanent=True), name='admin-socio'),
    path('admin/socios/listado/', SocioAdminListView.as_view(), name='admin-socio-listado'),
    path('admin/socios/crear/', SocioAdminCreateView.as_view(), name='admin-socio-crear'),
    path('admin/socios/<int:pk>/', SocioAdminDetailView.as_view(), name='admin-socio-detalle'),
    path('admin/socios/<int:pk>/editar/', SocioAdminUpdateView.as_view(), name='admin-socio-editar'),
    path('admin/socios/<int:socio_pk>/<int:history_pk>/', socio_history_pdf, name='socio-history-pdf'),
    path('admin/socios/ajax/', socio_admin_ajax, name='admin-socio-ajax'),

    # URLs de socios (usuarios)
    path('socio/mis_datos/', SocioFormView.as_view(), name='socio-datos'),

    # URLs de solicitud de socio (administración)
    path('admin/socios/solicitudes/', SolicitudAdminListView.as_view(), name='admin-socio-solicitudes'),

    # URLs de solicitud de socio (usuario)
    path('solicitud/', SolicitudView.as_view(), name='solicitud-crear'),

    # URLs de cuotas de socios (administración)
    path('admin/cuotas/', lambda request: redirect('admin-cuota-listado', permanent=True), name='admin-cuota'),
    path('admin/cuotas/listado/', CuotaSocialAdminListView.as_view(), name='admin-cuota-listado'),
    path('admin/cuotas/<int:pk>/eliminar/', cuota_delete, name='admin-cuota-eliminar'),
    path('admin/cuotas/<int:cuota_pk>/<int:history_pk>/', cuota_history_pdf, name='cuota-history-pdf'),

    # URLs de cuotas de socios (usuario)
    path('cuotas/mis_cuotas/', CuotaSocialListView.as_view(), name='socio-cuotas'),
    path('cuotas/reporte/<int:pk>/', cuota_social_pdf, name='cuotas-pdf'),
]
