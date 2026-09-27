from django.urls import path

from .views import MiPerfilProveedorView, MisZonasAtencionView, ProveedorDetalleView


urlpatterns = [
    path(
        'mi-perfil/',
        MiPerfilProveedorView.as_view(),
        name='mi-perfil-proveedor',
    ),
    path(
        'mis-zonas/',
        MisZonasAtencionView.as_view(),
        name='mis-zonas-atencion',
    ),
    # HU-09 / HU-10: perfil público del proveedor con su catálogo activo
    path('<int:pk>/', ProveedorDetalleView.as_view(), name='detalle-proveedor'),
]
