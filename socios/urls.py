from django.urls import path

# TODO: Importar las vistas de socios que se van a utilizar en las URLs
#       Crear las urls para la creación de un socio, la edición de un socio,
#       la eliminación de un socio y el listado de socios.

from django.urls import path
from django.views.generic import TemplateView

from .views import *

urlpatterns = [
    # Socios
    path('socios/', SocioListView.as_view(), name='socio-listado'),
    path('socios/crear/', SocioCreateView.as_view(), name='socio-crear'),
    path('socios/<int:pk>/', SocioDetailView.as_view(), name='socio-detalle'),
    path('socios/<int:pk>/editar/', socio_update_view, name='socio-editar'),
    path('socios/<int:pk>/eliminar/', socio_delete, name='socio-eliminar'),
    path('socios/<int:pk>/restaurar/', socio_restore, name='socio-restaurar'),

    # Miembros
    path('socios/<int:pk>/crear-miembro/', miembro_create_view, name='miembro-crear'),
    path('socios/miembro/<int:miembro_pk>', miembro_detail_view, name='miembro-detalle'),
    path('socios/miembro/<int:miembro_pk>/editar/', miembro_update_view, name='miembro-editar'),
]
