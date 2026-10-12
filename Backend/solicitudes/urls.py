from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClienteSolicitudesViewSet

router = DefaultRouter()
router.register(r'mis-solicitudes', ClienteSolicitudesViewSet, basename='mis-solicitudes')

urlpatterns = [
    path('', include(router.urls)),
]