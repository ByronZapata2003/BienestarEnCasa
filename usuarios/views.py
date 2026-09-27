from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from .models import Direccion, PerfilProveedor, PerfilUsuario, ZonaAtencion

from .serializers import ZonaAtencionSerializer, PerfilProveedorSerializer, ActualizarPerfilSerializer, CerrarSesionSerializer, DireccionSerializer, InicioSesionSerializer, PerfilSerializer, RegistroSerializer

from catalogo.models import Servicio
from catalogo.serializers import ServicioSerializer

class RegistroView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegistroSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        perfil = serializer.save()
        return Response(PerfilSerializer(perfil).data, status=status.HTTP_201_CREATED)


class InicioSesionView(TokenObtainPairView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = InicioSesionSerializer


class CerrarSesionView(APIView):
    def post(self, request):
        serializer = CerrarSesionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MiPerfilView(generics.RetrieveUpdateAPIView):
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return ActualizarPerfilSerializer

        return PerfilSerializer

    def get_object(self):
        return self.request.user.perfil

class DireccionListCreateView(generics.ListCreateAPIView):
    serializer_class = DireccionSerializer

    def get_queryset(self):
        if self.request.user.perfil.rol != PerfilUsuario.Rol.CLIENTE:
            raise PermissionDenied('Solo los clientes pueden consultar direcciones.')

        return Direccion.objects.filter(
            usuario=self.request.user
        ).order_by('-es_principal', '-creada_en')

    def perform_create(self, serializer):
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

    def get_queryset(self):
        if self.request.user.perfil.rol != PerfilUsuario.Rol.CLIENTE:
            raise PermissionDenied('Solo los clientes pueden consultar direcciones.')

        return Direccion.objects.filter(usuario=self.request.user)

    def perform_update(self, serializer):
        direccion = self.get_object()
        es_principal = serializer.validated_data.get('es_principal')

        if es_principal is True:
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
    def verificar_proveedor(self, request):
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

# HU-10: Consulta del perfil del proveedor y detalle del servicio
class PerfilProveedorPublicoView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, proveedor_id):
        try:
            perfil = PerfilProveedor.objects.select_related('perfil_usuario__usuario').get(pk=proveedor_id)
        except PerfilProveedor.DoesNotExist:
            return Response(
                {'error': 'El proveedor solicitado no fue encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        data = PerfilProveedorSerializer(perfil).data
        usuario = perfil.perfil_usuario.usuario
        data['nombres'] = usuario.first_name
        data['apellidos'] = usuario.last_name
        data['email'] = usuario.email
        data['telefono'] = perfil.perfil_usuario.telefono

        zonas = perfil.zonas_atencion.all()
        data['zonas_atencion'] = ZonaAtencionSerializer(zonas, many=True).data
        data['tiene_zonas_registradas'] = zonas.exists()

        if not zonas.exists():
            data['mensaje_zonas'] = 'El proveedor no tiene zonas generales de atención registradas.'

        servicios = Servicio.objects.filter(proveedor=perfil, estado=Servicio.Estado.ACTIVO)
        data['catalogo_servicios'] = ServicioSerializer(servicios, many=True).data

        return Response(data, status=status.HTTP_200_OK)