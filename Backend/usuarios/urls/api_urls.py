from django.urls import path

from ..views import DireccionDetalleView, DireccionListCreateView


urlpatterns = [
    path('direcciones/', DireccionListCreateView.as_view(), name='direcciones'),
    path('direcciones/<int:pk>/', DireccionDetalleView.as_view(), name='detalle-direccion',),
]