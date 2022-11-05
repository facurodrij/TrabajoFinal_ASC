from django.urls import path

from socios.views.socio.views import *
from socios.views.miembro.views import *

urlpatterns = [
    # Socios
    path('socios/', SocioListView.as_view(), name='socio-listado'),
    path('socios/crear/', SocioCreateView.as_view(), name='socio-crear'),
    path('socios/<int:pk>/', SocioDetailView.as_view(), name='socio-detalle'),
    path('socios/<int:pk>/editar/', SocioUpdateView.as_view(), name='socio-editar'),
    path('socios/<int:pk>/eliminar/', socio_delete, name='socio-eliminar'),
    path('socios/<int:pk>/restaurar/', socio_restore, name='socio-restaurar'),

    # Miembros
    path('miembros/', MiembroListView.as_view(), name='miembro-listado'),
    path('miembros/crear/', MiembroCreateView.as_view(), name='miembro-crear'),
    path('miembros/<int:pk>', MiembroDetailView.as_view(), name='miembro-detalle'),
    path('miembros/<int:pk>/eliminar/', miembro_delete, name='miembro-eliminar'),
    path('miembros/<int:pk>/restaurar/', miembro_restore, name='miembro-restaurar'),

    # Miembros
    path('socios/<int:pk>/crear-miembro/', miembro_create_view, name='socio-miembro-crear'),
    path('socios/miembro/<int:miembro_pk>/editar/', miembro_update_view, name='miembro-editar'),
]
