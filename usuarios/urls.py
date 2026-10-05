from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import CerrarSesionView, InicioSesionView, MiPerfilView, RegistroView


urlpatterns = [
    path('registro/', RegistroView.as_view(), name='registro'), #registra
    path('iniciar-sesion/', InicioSesionView.as_view(), name='iniciar-sesion'), #inicia
    path('renovar-token/', TokenRefreshView.as_view(), name='renovar-token'), #lo del token
    path('cerrar-sesion/', CerrarSesionView.as_view(), name='cerrar-sesion'), #depues de cerrar dispara la view para ejecturar la logica de cerrar sesion, sobre todo la de la lista negra de tokens
    path('mi-perfil/', MiPerfilView.as_view(), name='mi-perfil'), #carga el perfl del que este logueado
]
