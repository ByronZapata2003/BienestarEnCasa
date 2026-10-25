from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
import uuid

class PerfilUsuario(models.Model):
    class Rol(models.TextChoices):
        CLIENTE = 'CLIENTE', 'Cliente'
        PROVEEDOR = 'PROVEEDOR', 'Proveedor'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    rol = models.CharField(max_length=12, choices=Rol.choices)
    telefono = models.CharField(max_length=20, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'perfil de usuario'
        verbose_name_plural = 'perfiles de usuario'

    def __str__(self):
        return f'{self.usuario.email or self.usuario.username} ({self.get_rol_display()})'

class Direccion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='direcciones')
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    barrio = models.CharField(max_length=100)
    complemento = models.TextField(blank=True, null=True)
    es_principal = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'dirección'
        verbose_name_plural = 'direcciones'

    def __str__(self):
        return f'{self.direccion}, {self.barrio_sector} - {self.ciudad}'

class PerfilProveedor(models.Model):
    perfil_usuario = models.OneToOneField(
        PerfilUsuario,
        on_delete=models.CASCADE,
        related_name='perfil_profesional',
    )
    descripcion_profesional = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'perfil profesional'
        verbose_name_plural = 'perfiles profesionales'

    def __str__(self):
        return f'Perfil profesional de {self.perfil_usuario.usuario.email}'


class ZonaAtencion(models.Model):
    perfil_proveedor = models.ForeignKey(
        PerfilProveedor,
        on_delete=models.CASCADE,
        related_name='zonas_atencion',
    )
    ciudad = models.CharField(max_length=100)
    barrio_sector = models.CharField(max_length=150)

    class Meta:
        verbose_name = 'zona de atención'
        verbose_name_plural = 'zonas de atención'

    def __str__(self):
        return f'{self.barrio_sector}, {self.ciudad}'

class SesionActiva(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sesion_activa'
    )
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    refresh_jti = models.CharField(max_length=255)
    dispositivo = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Sesión de {self.usuario}'


class DisponibilidadProveedor(models.Model):
    DIAS_SEMANA = (
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    )

    proveedor = models.ForeignKey(
        PerfilProveedor,
        on_delete=models.CASCADE,
        related_name='disponibilidades',
    )
    dia_semana = models.PositiveSmallIntegerField(choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        ordering = ('dia_semana',)
        constraints = [
            models.CheckConstraint(
                condition=Q(hora_inicio__lt=F('hora_fin')),
                name='disponibilidad_hora_inicio_anterior_fin',
            ),
            models.UniqueConstraint(
                fields=('proveedor', 'dia_semana'),
                name='disponibilidad_bloque_unico',
            ),
        ]

    def clean(self):
        super().clean()
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError({'hora_fin': 'La hora inicial debe ser anterior a la hora final.'})

    def __str__(self):
        return f'{self.proveedor} - {self.get_dia_semana_display()} ({self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M})'


class PeriodoNoDisponible(models.Model):
    proveedor = models.ForeignKey(
        PerfilProveedor,
        on_delete=models.CASCADE,
        related_name='periodos_no_disponibles',
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    motivo = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ('fecha_inicio',)
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_inicio__lte=F('fecha_fin')),
                name='periodo_fecha_inicio_no_posterior_fin',
            ),
        ]

    def clean(self):
        super().clean()
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError({'fecha_fin': 'La fecha de inicio no puede ser posterior a la fecha de fin.'})

    def __str__(self):
        return f'{self.proveedor} - {self.fecha_inicio} a {self.fecha_fin}'
