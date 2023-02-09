from django.shortcuts import redirect
from django.urls import path

from core.views.admin.club.views import ClubFormView
from core.views.admin.estadistica.views import EstadisticaAdminView
from core.views.admin.persona.views import *
from core.views.user.index.views import IndexView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    # path('admin/', IndexAdminView.as_view(), name='index_admin'), # TODO: Diseñar este index
    path('admin/', lambda request: redirect('admin-club-form', permanent=True), name='index_admin'),

    # URLs del club (administración)
    path('admin/club/', lambda request: redirect('admin-club-form', permanent=True), name='club'),
    path('admin/club/detalles/', ClubFormView.as_view(), name='admin-club-form'),

    # URLs de persona (administración)
    path('admin/personas/', lambda request: redirect('admin-persona-listado', permanent=True), name='admin-persona'),
    path('admin/personas/listado/', PersonaAdminListView.as_view(), name='admin-persona-listado'),
    path('admin/personas/crear/', PersonaAdminCreateView.as_view(), name='admin-persona-crear'),
    # path('admin/club/personas/<int:pk>/', PersonaAdminDetailView.as_view(), name='admin-club-persona-detalle'),
    path('admin/personas/<int:pk>/editar/', PersonaAdminUpdateView.as_view(), name='admin-persona-editar'),
    path('admin/personas/comprobante/', persona_history_pdf, name='admin-persona-comprobante'),

    path('admin/estadisticas/', EstadisticaAdminView.as_view(), name='admin-estadisticas'),
]
