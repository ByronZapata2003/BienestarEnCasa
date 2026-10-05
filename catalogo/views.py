from django.db.models import Q
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, viewsets, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import Categoria, Servicio, ContenidoMultimediaServicio, ElementoServicio
from .serializers import (
    CategoriaSerializer,
    ServicioSerializer,
    ServicioUpdateSerializer,
    ContenidoMultimediaServicioSerializer,
    ElementoServicioSerializer,
)
from .permissions import IsProveedorOwnerOrReadOnly, IsProviderOwner, es_dueno_servicio


def filtrar_visibles(queryset, user, prefijo=''):
    #cuando consulta un cliente o el proveedr que no es dueño, le muestra solo activo si no los otros
    """Servicios activos para todos; los inactivos solo para su proveedor dueño."""
    return queryset.filter(
        Q(**{f'{prefijo}estado': Servicio.Estado.ACTIVO})
        | Q(**{f'{prefijo}proveedor__perfil_usuario__usuario': user})
    )


class ServicioGestionView(generics.RetrieveUpdateAPIView):
    serializer_class = ServicioUpdateSerializer
    # CA6: IsAuthenticated deniega acceso a usuarios sin sesión
    # CA5: IsProviderOwner deniega operaciones sobre servicios ajenos
    permission_classes = [permissions.IsAuthenticated, IsProviderOwner]

    def get_queryset(self):
        """CA1 y CA5: solo servicios del proveedor autenticado."""
        return Servicio.objects.filter(proveedor__perfil_usuario__usuario=self.request.user)

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.IsAuthenticated]
    #sirve para traer todas las categorias y llama a serilizer


class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.select_related(
        'categoria', 'proveedor__perfil_usuario__usuario'
    ).prefetch_related('multimedia', 'elementos')
    serializer_class = ServicioSerializer
    permission_classes = [permissions.IsAuthenticated, IsProveedorOwnerOrReadOnly]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['categoria']
    search_fields = [
        'nombre',
        'proveedor__perfil_usuario__usuario__first_name',
        'proveedor__perfil_usuario__usuario__last_name',
        'proveedor__perfil_usuario__usuario__username',
    ]

    def get_queryset(self): #filtra
        return filtrar_visibles(super().get_queryset(), self.request.user)

    def perform_create(self, serializer):
        # HU-06: Validar que solo los proveedores asocien servicios a su catálogo
        user = self.request.user
        if not hasattr(user, 'perfil') or user.perfil.rol != 'PROVEEDOR':
            raise PermissionDenied("No tienes permisos de proveedor para registrar servicios.")

        if not hasattr(user.perfil, 'perfil_profesional'):
            raise PermissionDenied("Primero debes registrar tu perfil profesional de proveedor.")

        serializer.save(proveedor=user.perfil.perfil_profesional)

    # HU-10: Detalle de servicio
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return Response(
                {"error": "El servicio solicitado no fue encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(self.get_serializer(instance).data)


class DetalleServicioViewSet(viewsets.ModelViewSet): #para traer los datos del servicio y solo el dueño puede escribir
    """Base para multimedia y elementos: solo el dueño del servicio escribe (HU-08)."""
    permission_classes = [permissions.IsAuthenticated, IsProveedorOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['servicio']

    def get_queryset(self):
        return filtrar_visibles(super().get_queryset(), self.request.user, 'servicio__')
    #de aqui pa abajo verifica que sea la persona que creo el servicio y si no es, no puede modificarlo
    def verificar_servicio(self, serializer):
        servicio = serializer.validated_data.get('servicio') or serializer.instance.servicio
        if not es_dueno_servicio(self.request.user, servicio): #verifica si el dueño 
            raise PermissionDenied("Solo el proveedor dueño del servicio puede modificar su contenido.")
    #lo manda a crear
    def perform_create(self, serializer):
        self.verificar_servicio(serializer)
        serializer.save()
    #lo manda a actualizar
    def perform_update(self, serializer):
        self.verificar_servicio(serializer)
        serializer.save()


class ContenidoMultimediaServicioViewSet(DetalleServicioViewSet):
    queryset = ContenidoMultimediaServicio.objects.select_related('servicio')
    serializer_class = ContenidoMultimediaServicioSerializer
    #para traer los datos del servicio y solo el dueño puede escribir, hereda de DetalleServicioViewSet


class ElementoServicioViewSet(DetalleServicioViewSet):
    queryset = ElementoServicio.objects.select_related('servicio')
    serializer_class = ElementoServicioSerializer
    # lo mismo de arriba pero para elementos
