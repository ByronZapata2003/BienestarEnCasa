from django.shortcuts import render

from rest_framework import viewsets, permissions, status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import Categoria, Servicio
from .serializers import CategoriaSerializer, ServicioSerializer, ServicioUpdateSerializer
from .permissions import IsProveedor, IsProveedorOwnerOrReadOnly, IsProviderOwner

class ServicioGestionView(generics.RetrieveUpdateAPIView):
    serializer_class = ServicioUpdateSerializer
    # CA6: IsAuthenticated deniega acceso a usuarios sin sesión
    # CA5: IsProviderOwner deniega operaciones sobre servicios ajenos
    permission_classes = [IsAuthenticated, IsProviderOwner]

    def get_queryset(self):
        """
        Refuerzo de seguridad para el CA1 y CA5: 
        Filtra el queryset base para que solo retorne servicios del proveedor autenticado.
        """
        # Ajustar 'proveedor__usuario' según la estructura exacta de tus modelos
        return Servicio.objects.filter(proveedor__usuario=self.request.user)

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.IsAuthenticated]


class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.all().select_related('categoria', 'proveedor__perfil_usuario__usuario')
    serializer_class = ServicioSerializer
    permission_classes = [permissions.IsAuthenticated, IsProveedorOwnerOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # HU-09: Búsqueda por nombre o categoría
        busqueda = self.request.query_params.get('search', None)
        categoria_id = self.request.query_params.get('categoria', None)

        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda) | 
                Q(descripcion__icontains=busqueda) |
                Q(categoria__nombre__icontains=busqueda)
            )

        if categoria_id:
            queryset = queryset.filter(categoria_id=categoria_id)

        return queryset

    def perform_create(self, serializer):
        # HU-06: Validar que solo los proveedores asocien servicios a su catálogo
        user = self.request.user
        if not hasattr(user, 'perfil') or user.perfil.rol != 'PROVEEDOR':
            raise permissions.PermissionDenied("No tienes permisos de proveedor para registrar servicios.")

        if not hasattr(user.perfil, 'perfil_profesional'):
            raise permissions.PermissionDenied("Primero debes registrar tu perfil profesional de proveedor.")

        serializer.save(proveedor=user.perfil.perfil_profesional)

    def list(self, request, *args, **kwargs):
        # HU-09: Manejo del criterio de búsqueda cuando no arroja resultados
        response = super().list(request, *args, **kwargs)
        busqueda = request.query_params.get('search', None)
        
        if busqueda and len(response.data) == 0:
            return Response(
                {
                    "mensaje": f"No se encontraron servicios que coincidan con '{busqueda}'.",
                    "resultados": []
                },
                status=status.HTTP_200_OK
            )
        return response