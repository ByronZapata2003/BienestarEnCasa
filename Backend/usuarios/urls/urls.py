from django.urls import path

from ..views import CerrarSesionView, InicioSesionView, MiPerfilView, RegistroView, RenovarTokenView


urlpatterns = [
    path('registro/', RegistroView.as_view(), name='registro'), #registra
    path('iniciar-sesion/', InicioSesionView.as_view(), name='iniciar-sesion'), #inicia
    path('renovar-token/', RenovarTokenView.as_view(), name='renovar-token'), #lo del token
    path('cerrar-sesion/', CerrarSesionView.as_view(), name='cerrar-sesion'), #depues de cerrar dispara la view para ejecturar la logica de cerrar sesion, sobre todo la de la lista negra de tokens
    path('mi-perfil/', MiPerfilView.as_view(), name='mi-perfil'), #carga el perfl del que este logueado
]
