from django.urls import path

from core.views import *
from parameters.views import ParametersClubFormView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('admin/club/', lambda request: redirect('club-detalles', permanent=True), name='club'),
    path('admin/club/detalles/', club, name='club-detalles'),
    path('admin/club/parametros/', ParametersClubFormView.as_view(), name='admin-club-parametros'),
    # path('admin/club/personas/listado/','),

]
