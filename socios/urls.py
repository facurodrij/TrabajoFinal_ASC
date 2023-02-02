from django.urls import path

from socios.views.admin.categoria.views import *
from socios.views.admin.cuota.views import *
from socios.views.admin.socio.views import *
from socios.views.user.cuota.views import *
from socios.views.user.socio.views import *

urlpatterns = [
    # # URLs de socios (administración)
    # Si ingresan a admin/socios/ se redirige a admin-socio-listado
    path('admin/socios/', lambda request: redirect('admin-socio-listado', permanent=True), name='admin-socio'),
    path('admin/socios/listado/', SocioAdminListView.as_view(), name='admin-socio-listado'),
    path('admin/socios/crear/', SocioAdminCreateView.as_view(), name='admin-socio-crear'),
    path('admin/socios/<int:pk>/', SocioAdminDetailView.as_view(), name='admin-socio-detalle'),
    path('admin/socios/<int:pk>/editar/', SocioAdminUpdateView.as_view(), name='admin-socio-editar'),
    path('admin/socios/<int:pk>/baja/', SocioAdminDeleteView.as_view(), name='admin-socio-baja'),
    path('admin/socios/<int:pk>/restaurar/', SocioAdminRestoreView.as_view(), name='admin-socio-restaurar'),
    path('admin/socios/<int:socio_pk>/<int:history_pk>/', socio_history_pdf, name='socio-history-pdf'),
    path('admin/socios/ajax/', socio_admin_ajax, name='admin-socio-ajax'),
    path('admin/socio/parametros/', ParametersSocioFormView.as_view(), name='admin-socio-parametros'),

    # URLs de socios (usuarios)
    path('socio/perfil/', SocioUserView.as_view(), name='socio-perfil'),

    # URLs de cuotas de socios (administración)
    path('admin/cuotas/', lambda request: redirect('admin-cuota-listado', permanent=True), name='admin-cuota'),
    path('admin/cuotas/listado/', CuotaSocialAdminListView.as_view(), name='admin-cuota-listado'),
    path('admin/cuotas/<int:pk>/eliminar/', cuota_delete, name='admin-cuota-eliminar'),
    path('admin/cuotas/<int:cuota_pk>/<int:history_pk>/', cuota_history_pdf, name='cuota-history-pdf'),

    # URLs de cuotas de socios (usuario)
    path('cuotas/mis_cuotas/', CuotaSocialListView.as_view(), name='socio-cuotas'),
    path('cuotas/reporte/<int:pk>/', cuota_social_pdf, name='cuotas-pdf'),

    # URLs de categorias de socios (administración)
    path('admin/socios/categorias/', CategoriaAdminListView.as_view(), name='admin-categoria-listado'),
    path('admin/socios/categorias/crear/', CategoriaAdminCreateView.as_view(), name='admin-categoria-crear'),
    path('admin/socios/categorias/<int:pk>/editar/', CategoriaAdminUpdateView.as_view(), name='admin-categoria-editar'),
]
