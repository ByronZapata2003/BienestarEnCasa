from django.urls import path

from .views import MiPerfilProveedorView, MisZonasAtencionView, PerfilProveedorPublicoView


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
    # HU-10: Ruta pública para consultar perfil y catálogo
    path(
        '<int:proveedor_id>/',
        PerfilProveedorPublicoView.as_view(),
        name='perfil-proveedor-publico',
    ),
]
