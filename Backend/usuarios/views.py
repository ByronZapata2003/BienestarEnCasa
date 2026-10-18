from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from .models import Direccion, PerfilProveedor, PerfilUsuario, ZonaAtencion, SesionActiva


from catalogo.models import Servicio
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import render
from .serializers import ProveedorPublicoSerializer, ZonaAtencionSerializer, PerfilProveedorSerializer, ActualizarPerfilSerializer, DireccionSerializer, InicioSesionSerializer, PerfilSerializer, RegistroSerializer

from catalogo.models import Servicio
from catalogo.serializers import ServicioSerializer

class RegistroView(generics.CreateAPIView): #para crear el usuario despues de registrarse
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    serializer_class = RegistroSerializer #llama al serializer para que haga la validacion de los datos y cree el usuario y el perfil

    def create(self, request, *args, **kwargs): #lo crea
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)#el serializer ya verifico
        perfil = serializer.save() 
        return Response(PerfilSerializer(perfil).data, status=status.HTTP_201_CREATED)


def poner_cookies(response): #saca los tokens del body y los manda como cookies httponly, asi el JS nunca los ve
    for nombre, vida in (('access', jwt_settings.ACCESS_TOKEN_LIFETIME), ('refresh', jwt_settings.REFRESH_TOKEN_LIFETIME)):
        if nombre in response.data:
            response.set_cookie(nombre, response.data.pop(nombre), max_age=int(vida.total_seconds()),
                                httponly=True, secure=not settings.DEBUG, samesite='Lax')
    return response


class InicioSesionView(TokenObtainPairView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = () #una cookie vieja o de otra sesion no debe impedir volver a entrar
    serializer_class = InicioSesionSerializer
     #inicia la seccion y el serializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh = RefreshToken(response.data['refresh'])
        usuario_id = refresh[jwt_settings.USER_ID_CLAIM]

        # invalida cualquier refresh token anterior de este usuario
        for t in OutstandingToken.objects.filter(user_id=usuario_id).exclude(jti=refresh['jti']):
            BlacklistedToken.objects.get_or_create(token=t)

        # registra esta como la sesion vigente
        SesionActiva.objects.update_or_create(
            usuario_id=usuario_id,
            defaults={
                'session_id': refresh['sid'],
                'refresh_jti': refresh['jti'],
                'dispositivo': request.META.get('HTTP_USER_AGENT', '')[:255],
                'ip': request.META.get('REMOTE_ADDR'),
            }
        )
        return poner_cookies(response)


class RenovarTokenView(TokenRefreshView):
    authentication_classes = ()
    def get_serializer(self, *args, **kwargs): #el refresh sale de la cookie, no del body
        kwargs['data'] = {'refresh': self.request.COOKIES.get('refresh', '')}
        return super().get_serializer(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        return poner_cookies(super().post(request, *args, **kwargs))


class CerrarSesionView(APIView):
    permission_classes = (permissions.AllowAny,) #aunque el access ya haya vencido se deben poder borrar las cookies
    authentication_classes = () #la sesion se saca del refresh, asi una sesion reemplazada tambien puede borrar sus cookies

    def post(self, request):
        refresh = request.COOKIES.get('refresh')
        if refresh:
            try:
                token = RefreshToken(refresh)
                #solo borra la sesion si es la vigente, no la de otro dispositivo
                SesionActiva.objects.filter(usuario_id=token[jwt_settings.USER_ID_CLAIM], session_id=token.get('sid')).delete()
                token.blacklist() #lista negra pa que nadie lo use mas
            except TokenError:
                pass #ya vencido o invalido, igual se borran las cookies
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie('access', samesite='Lax')
        response.delete_cookie('refresh', samesite='Lax')
        return response


class MiPerfilView(generics.RetrieveUpdateAPIView):
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'PATCH': #este es para modificar
            return ActualizarPerfilSerializer

        return PerfilSerializer

    def get_object(self):
        return self.request.user.perfil

class DireccionListCreateView(generics.ListCreateAPIView):
    serializer_class = DireccionSerializer
    #envia lo que tiene que hacer y respuestas al html
    def get_queryset(self):
        if self.request.user.perfil.rol != PerfilUsuario.Rol.CLIENTE:
            raise PermissionDenied('Solo los clientes pueden consultar direcciones.')

        return Direccion.objects.filter(
            usuario=self.request.user
        ).order_by('-es_principal', '-creada_en')

    def perform_create(self, serializer): #aqui la crea y verifico si es cliente o no
        if self.request.user.perfil.rol != PerfilUsuario.Rol.CLIENTE:
            raise PermissionDenied('Solo los clientes pueden registrar direcciones.')

        existe_direccion_principal = Direccion.objects.filter(
            usuario=self.request.user,
            es_principal=True,
        ).exists()

        es_principal = serializer.validated_data.get('es_principal', False)

        if es_principal:
            Direccion.objects.filter(
                usuario=self.request.user,
                es_principal=True,
            ).update(es_principal=False)

        serializer.save(
            usuario=self.request.user,
            es_principal=es_principal or not existe_direccion_principal,
        )

class DireccionDetalleView(generics.RetrieveUpdateAPIView):
    serializer_class = DireccionSerializer

    def get_queryset(self): # antes de pedirla verifica que se el cliente
        if self.request.user.perfil.rol != PerfilUsuario.Rol.CLIENTE:
            raise PermissionDenied('Solo los clientes pueden consultar direcciones.')

        return Direccion.objects.filter(usuario=self.request.user)

    def perform_update(self, serializer):
        direccion = self.get_object()
        es_principal = serializer.validated_data.get('es_principal')

        if es_principal is True: #verifica si es principal y si ya hay otra principal, si es asi la cambia a false
            Direccion.objects.filter(
                usuario=self.request.user,
                es_principal=True,
            ).exclude(pk=direccion.pk).update(es_principal=False)

        if es_principal is False and direccion.es_principal:
            existe_otra_principal = Direccion.objects.filter(
                usuario=self.request.user,
                es_principal=True,
            ).exclude(pk=direccion.pk).exists()

            if not existe_otra_principal:
                raise ValidationError(
                    {'es_principal': 'Debe existir al menos una dirección principal.'}
                )

        serializer.save()

class MiPerfilProveedorView(APIView):
    def verificar_proveedor(self, request):#comprueba si es proveedor, si no lo es lanza un error
        if request.user.perfil.rol != PerfilUsuario.Rol.PROVEEDOR:
            raise PermissionDenied(
                'Solo los proveedores pueden gestionar su perfil profesional.'
            )

    def obtener_perfil(self, request):
        try:
            return request.user.perfil.perfil_profesional
        except PerfilProveedor.DoesNotExist:
            raise NotFound('Aún no has creado tu perfil profesional.')

    def get(self, request):
        self.verificar_proveedor(request)
        perfil = self.obtener_perfil(request)
        return Response(PerfilProveedorSerializer(perfil).data)

    def post(self, request):
        self.verificar_proveedor(request)

        if hasattr(request.user.perfil, 'perfil_profesional'):
            raise ValidationError(
                'Ya existe un perfil profesional para este proveedor.'
            )

        serializer = PerfilProveedorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        perfil = serializer.save(perfil_usuario=request.user.perfil)

        return Response(
            PerfilProveedorSerializer(perfil).data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request):
        self.verificar_proveedor(request)
        perfil = self.obtener_perfil(request)

        serializer = PerfilProveedorSerializer(
            perfil,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

class MisZonasAtencionView(generics.ListCreateAPIView):
    serializer_class = ZonaAtencionSerializer

    def obtener_perfil_proveedor(self):
        if self.request.user.perfil.rol != PerfilUsuario.Rol.PROVEEDOR:
            raise PermissionDenied(
                'Solo los proveedores pueden gestionar zonas de atención.'
            )

        try:
            return self.request.user.perfil.perfil_profesional
        except PerfilProveedor.DoesNotExist:
            raise NotFound(
                'Primero debes crear tu perfil profesional.'
            )

    def get_queryset(self):
        perfil_proveedor = self.obtener_perfil_proveedor()
        return ZonaAtencion.objects.filter(
            perfil_proveedor=perfil_proveedor
        )

    def perform_create(self, serializer):
        perfil_proveedor = self.obtener_perfil_proveedor()
        serializer.save(perfil_proveedor=perfil_proveedor)


class ProveedorDetalleView(generics.RetrieveAPIView): #catalogo
    """Perfil público del proveedor con su catálogo activo (HU-09, HU-10)."""
    serializer_class = ProveedorPublicoSerializer
    queryset = PerfilProveedor.objects.select_related('perfil_usuario__usuario').prefetch_related(
        'zonas_atencion',
        Prefetch(
            'servicios',
            queryset=Servicio.objects.filter(estado=Servicio.Estado.ACTIVO)
            .select_related('categoria', 'proveedor__perfil_usuario__usuario')
            .prefetch_related('multimedia', 'elementos'),
        ),
    )

    def retrieve(self, request, *args, **kwargs):
        try:
            perfil = self.get_object()
        except Http404:
            return Response(
                {'error': 'El proveedor solicitado no fue encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        data = self.get_serializer(perfil).data
        data['email'] = perfil.perfil_usuario.usuario.email
        data['telefono'] = perfil.perfil_usuario.telefono
        data['tiene_zonas_registradas'] = bool(data['zonas_atencion'])
        if not data['zonas_atencion']:
            data['mensaje_zonas'] = 'El proveedor no tiene zonas generales de atención registradas.'
        return Response(data)
