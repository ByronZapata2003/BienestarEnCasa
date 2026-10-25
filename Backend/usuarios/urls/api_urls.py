from django.urls import path
from ..views import DireccionDetalleView, DireccionListCreateView, MiPerfilView

urlpatterns = [
    # Ruta para ver y editar el perfil del usuario autenticado
    path('perfil/', MiPerfilView.as_view(), name='mi-perfil-usuario'),

    # Ruta para direcciones
    path('direcciones/', DireccionListCreateView.as_view(), name='direcciones'),
    path('direcciones/<int:pk>/', DireccionDetalleView.as_view(), name='detalle-direccion'),
]