from django.shortcuts import redirect
from django.urls import path

from core.views.admin.club.views import club
from core.views.admin.index.views import IndexAdminView
from core.views.user.index.views import IndexView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('admin/', IndexAdminView.as_view(), name='index_admin'),

    # URLs del club (administración)
    path('admin/club/', lambda request: redirect('admin-club-detalles', permanent=True), name='club'),
    path('admin/club/detalles/', club, name='admin-club-detalles'),

]
