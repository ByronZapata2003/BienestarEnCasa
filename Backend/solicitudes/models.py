from django.db import models
from django.conf import settings
from catalogo.models import Servicio
from usuarios.models import PerfilProveedor, Direccion

class SolicitudReserva(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        SUGERIDA = 'SUGERIDA', 'Sugerida'
        ACEPTADA = 'ACEPTADA', 'Aceptada'
        COMPLETADA = 'COMPLETADA', 'Completada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='solicitudes_cliente'
    )
    proveedor = models.ForeignKey(
        PerfilProveedor,
        on_delete=models.CASCADE,
        related_name='solicitudes_recibidas'
    )
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.SET_NULL,
        null=True,
        related_name='solicitudes'
    )

    # Copia de condiciones del servicio en la creación (RF-23 / RN-13)
    nombre_servicio_copia = models.CharField(max_length=150)
    precio_copia = models.DecimalField(max_digits=10, decimal_places=2)
    duracion_minutos_copia = models.PositiveIntegerField()

    # Datos del agendamiento y ubicación
    fecha_solicitada = models.DateField()
    hora_solicitada = models.TimeField()
    direccion_atencion = models.CharField(max_length=255)
    barrio_sector = models.CharField(max_length=100)
    informacion_complementaria = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)

    # Estado y motivo de cancelación/rechazo (HU-13)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)
    motivo_rechazo_cancelacion = models.TextField(blank=True, null=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'solicitud o reserva'
        verbose_name_plural = 'solicitudes y reservas'
        ordering = ['-creado_en']

    def __str__(self):
        return f"Solicitud #{self.id} - {self.nombre_servicio_copia} ({self.estado})"