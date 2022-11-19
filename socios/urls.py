from django.urls import path

from socios.views.socio.admin.views import *
from socios.views.socio.views import SocioFormView
from socios.views.solicitud.views import *

urlpatterns = [
    # Socios
    path('socios/', SocioListView.as_view(), name='socio-listado'),
    path('socios/<int:pk>/', SocioAdminDetailView.as_view(), name='socio-detalle'),
    path('socios/<int:pk>/editar/', SocioAdminUpdateView.as_view(), name='socio-editar'),
    path('socios/<int:pk>/eliminar/', socio_delete, name='socio-eliminar'),
    path('socios/<int:pk>/restaurar/', socio_restore, name='socio-restaurar'),
    path('socio/info/', SocioFormView.as_view(), name='socio-info'),

    # Solicitud de asociación
    path('solicitud/', SolicitudView.as_view(), name='solicitud-crear'),
    path('solicitud/listado/', SolicitudListView.as_view(), name='solicitud-listado'),

    # Cuotas sociales
    path('cuotas/<int:pk>/eliminar/', cuota_delete, name='cuota-eliminar'),
]
