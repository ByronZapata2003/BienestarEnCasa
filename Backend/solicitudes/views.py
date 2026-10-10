from django.shortcuts import render

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import SolicitudReserva
from .serializers import SolicitudReservaSerializer

class ClienteSolicitudesViewSet(viewsets.ModelViewSet):
    """
    Vista dedicada a la gestión y consulta de solicitudes/reservas del cliente (HU-13)
    """
    serializer_class = SolicitudReservaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # El cliente únicamente consulta sus propias solicitudes
        return SolicitudReserva.objects.filter(cliente=self.request.user)

    def perform_create(self, serializer):
        serializer.save(cliente=self.request.user)

    def list(self, request, *args, **kwargs):
        # Criterio de Aceptación 5 (HU-13): Cliente sin solicitudes registradas
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response(
                {"mensaje": "No tienes solicitudes o reservas registradas.", "resultados": []},
                status=status.HTTP_200_OK
            )
        return super().list(request, *args, **kwargs)