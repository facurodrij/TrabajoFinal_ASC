from django.urls import path

# TODO: Importar las vistas de socios que se van a utilizar en las URLs
#       Crear las urls para la creación de un socio, la edición de un socio,
#       la eliminación de un socio y el listado de socios.

from django.urls import path
from django.views.generic import TemplateView

from .views import *

urlpatterns = [
    path('socios/', socios, name='socios'),
]
