"""
URL configuration for BienestarEnCasa project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views

urlpatterns = [ #aqui definimos que se solicita y luego las urls de cada app pa que sepa que tenga que hacer y no este esa cantidad de urls aqui, sino que se mande a cada app y que haga lo que tenga que hacer
    path('admin/', admin.site.urls),
    path('api/auth/', include('usuarios.urls')),
    path('api/usuarios/', include('usuarios.api_urls')), # manda lo de usuarios no proveedores
    path('api/proveedores/', include('usuarios.proveedores_urls')), #manda pa proveedores
    path('api/catalogo/', include('catalogo.urls')), #manda el render para el calalogo
    path('api/solicitudes/', include('solicitudes.urls')),
    path('recuperar-password/', 
         auth_views.PasswordResetView.as_view(
             template_name='users/password_reset.html',
             email_template_name='users/password_reset_email.html',
             subject_template_name='users/password_reset_subject.txt'
         ), #para recuperar el password lo genera aqui mientras envia
         name='password_reset'),
    path('recuperar-password/enviado/', #deespues que genera el link
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('restablecer/<uidb64>/<token>/', #aqui para que recupere la contra
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('restablecer/completo/', #despues de que la restablecio
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) #esto es para todo el proyecto, aqui permite y en lo que se cambio en settings que se pueda carga lo que sea de media
