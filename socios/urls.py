from django.urls import path

from socios.views.socio.admin.views import *
from socios.views.socio.views import SocioFormView
from socios.views.solicitud.views import *

urlpatterns = [
    # Socios, URLs de administración
    path('admin/socios/', SocioAdminListView.as_view(), name='admin-socio-listado'),
    path('admin/socios/<int:pk>/', SocioAdminDetailView.as_view(), name='admin-socio-detalle'),
    path('admin/socios/<int:pk>/editar/', SocioAdminUpdateView.as_view(), name='admin-socio-editar'),
    path('admin/socios/<int:pk>/eliminar/', socio_delete, name='admin-socio-eliminar'),
    path('admin/socios/<int:pk>/restaurar/', socio_restore, name='admin-socio-restaurar'),

    # Socios, URLs de usuario
    path('socio/', SocioFormView.as_view(), name='socio'),

    # Solicitud de asociación, URLs de administración
    path('admin/solicitud_socios/', SolicitudAdminListView.as_view(), name='admin-solicitud-listado'),

    # Solicitud de asociación, URLs de usuario
    path('solicitud/', SolicitudView.as_view(), name='solicitud-crear'),

    # Cuotas sociales, URLs de administración
    path('admin/cuotas/<int:pk>/eliminar/', cuota_delete, name='admin-cuota-eliminar'),
]
