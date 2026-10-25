from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClienteSolicitudesViewSet

router = DefaultRouter()
# Registrar con r'' genera las rutas /api/solicitudes/ y asigna el nombre 'mis-solicitudes-list'
router.register(r'', ClienteSolicitudesViewSet, basename='mis-solicitudes')

urlpatterns = [
    path('', include(router.urls)),
]