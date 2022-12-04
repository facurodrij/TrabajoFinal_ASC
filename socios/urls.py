from django.urls import path

from parameters.views import ParametersSociosFormView
from socios.views.admin.cuota.views import *
from socios.views.admin.socio.views import *
from socios.views.cuota.views import *
from socios.views.socio.views import *
from socios.views.solicitud.views import *

urlpatterns = [
    # --URL SOCIOS--
    # Socios, URLs de administración
    # Si ingresan a admin/socios/ se redirige a admin-socio-listado
    path('admin/socios/', lambda request: redirect('admin-socio-listado', permanent=True), name='admin-socio'),
    path('admin/socios/listado/', SocioAdminListView.as_view(), name='admin-socio-listado'),
    path('admin/socios/<int:pk>/', SocioAdminDetailView.as_view(), name='admin-socio-detalle'),
    path('admin/socios/<int:pk>/editar/', SocioAdminUpdateView.as_view(), name='admin-socio-editar'),
    path('admin/socios/parametros/', ParametersSociosFormView.as_view(), name='admin-socio-parametros'),
    path('admin/socios/<int:socio_pk>/<int:history_pk>/', socio_history_pdf, name='socio-history-pdf'),
    # Socios, URLs de usuario
    path('socio/mis_datos/', SocioFormView.as_view(), name='socio-datos'),

    # --URL SOLICITUDES--
    # Solicitud de socios, URLs de administración
    path('admin/socios/solicitudes/', SolicitudAdminListView.as_view(), name='admin-socio-solicitudes'),
    # Solicitud de asociación, URLs de usuario
    path('solicitud/', SolicitudView.as_view(), name='solicitud-crear'),

    # --URL CUOTAS SOCIALES--
    # Cuotas sociales, URLs de administración
    path('admin/socios/cuotas/', CuotaSocialAdminListView.as_view(), name='admin-socio-cuotas'),
    path('admin/cuotas/<int:pk>/eliminar/', cuota_delete, name='admin-cuota-eliminar'),
    path('admin/cuotas/<int:cuota_pk>/<int:history_pk>/', cuota_history_pdf, name='cuota-history-pdf'),
    # Cuotas sociales, URLs de usuario
    path('socio/mis_cuotas/', CuotaSocialListView.as_view(), name='socio-cuotas'),
    # Cuotas sociales, URLs de usuario sin autenticación
    path('cuotas/reporte/<int:pk>/', cuota_social_pdf, name='cuotas-pdf'),
]
