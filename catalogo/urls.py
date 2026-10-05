from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoriaViewSet, ServicioViewSet, ServicioGestionView, ContenidoMultimediaServicioViewSet, ElementoServicioViewSet

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet, basename='categoria') # ruta pa las categorias y servicios
router.register(r'servicios', ServicioViewSet, basename='servicio') # ruta pa servicios
router.register(r'multimedia', ContenidoMultimediaServicioViewSet, basename='multimedia') #ruta pa multimedia
router.register(r'elementos', ElementoServicioViewSet, basename='elemento') #ruta pa los equipos o insumos o mas

urlpatterns = [
    path('', include(router.urls)),
    path('servicios/<int:pk>/gestion/', ServicioGestionView.as_view(), name='servicio-gestion'), ##ruta para la vista de gestión de servicios
]
