from django.urls import path
from django.views.generic import TemplateView

from .views import *

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('club/', club, name='club'),
    path('socios/', SocioListView.as_view(), name='socios'),
    path('socios/crear/', SocioCreateView.as_view(), name='crear_socio'),
    path('socios/<int:pk>/editar/', SocioUpdateView.as_view(), name='editar_socio'),
    path('socios/<int:pk>/eliminar/', socio_delete, name='eliminar_socio'),
    path('socios/<int:pk>/restaurar', socio_restore, name='restaurar_socio'),
]
