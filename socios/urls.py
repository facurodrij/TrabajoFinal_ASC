from django.urls import path
from django.shortcuts import redirect

from socios.views.admin.socio.views import *
from socios.views.socio.views import SocioFormView
from socios.views.solicitud.views import *

urlpatterns = [
    # Socios, URLs de administración

    # Si ingresan a admin/socios/ se redirige a admin-socio-listado
    path('admin/socios/', lambda request: redirect('admin-socio-listado', permanent=True), name='admin-socio'),
    path('admin/socios/listado/', SocioAdminListView.as_view(), name='admin-socio-listado'),
    path('admin/socios/solicitudes/', SolicitudAdminListView.as_view(), name='admin-socio-solicitudes'),
    # TODO: Agregar la vista del listado de cuotas sociales
    path('admin/socios/cuotas/', lambda request: redirect('admin-socio-listado', permanent=True),
         name='admin-socio-cuotas'),
    # TODO: Agregar la vista de parámetros socios
    path('admin/socios/parametros/', lambda request: redirect('admin-socio-listado', permanent=True),
         name='admin-socio-parametros'),
    path('admin/socios/<int:pk>/', SocioAdminDetailView.as_view(), name='admin-socio-detalle'),
    path('admin/socios/<int:pk>/editar/', SocioAdminUpdateView.as_view(), name='admin-socio-editar'),
    path('admin/socios/<int:pk>/eliminar/', socio_delete, name='admin-socio-eliminar'),
    path('admin/socios/<int:pk>/restaurar/', socio_restore, name='admin-socio-restaurar'),

    # Socios, URLs de usuario
    path('socio/', SocioFormView.as_view(), name='socio'),



    # Solicitud de asociación, URLs de usuario
    path('solicitud/', SolicitudView.as_view(), name='solicitud-crear'),

    # Cuotas sociales, URLs de administración
    path('admin/cuotas/<int:pk>/eliminar/', cuota_delete, name='admin-cuota-eliminar'),
]
