from django.urls import path

# TODO: Importar las vistas de socios que se van a utilizar en las URLs
#       Crear las urls para la creación de un socio, la edición de un socio,
#       la eliminación de un socio y el listado de socios.

from django.urls import path
from django.views.generic import TemplateView

from .views import *

urlpatterns = [
    path('socios/', socios, name='socios'),
    path('asociarse/', asociacion, name='asociarse'),
    path('socios/<int:pk>/', SocioIndividualDetailView.as_view(), name='socio-detail'),
    path('socios/<int:pk>/aprobar/', aprobar_socio, name='socio-aprobar'),
    path('socios/<int:pk>/rechazar/', rechazar_socio, name='socio-rechazar'),
]
