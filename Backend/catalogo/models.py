from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models
from usuarios.models import PerfilProveedor

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        INACTIVO = 'INACTIVO', 'Inactivo'

    proveedor = models.ForeignKey(
        PerfilProveedor,
        on_delete=models.CASCADE,
        related_name='servicios'
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='servicios'
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    duracion_minutos = models.PositiveIntegerField(help_text="Duración estimada en minutos")
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'servicio'
        verbose_name_plural = 'servicios'

    def __str__(self):
        return f"{self.nombre} - {self.proveedor.perfil_usuario.usuario.email}"


class Solicitud(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.DO_NOTHING)
    # Estos campos deben existir para congelar los valores al momento de crear la solicitud
    precio_historico = models.DecimalField(max_digits=10, decimal_places=2)
    nombre_historico = models.CharField(max_length=255)
    duracion_historica = models.IntegerField()

    def save(self, *args, **kwargs):
        if not self.pk: # Solo en la creación
            self.precio_historico = self.servicio.precio
            self.nombre_historico = self.servicio.nombre
            self.duracion_historica = self.servicio.duracion_minutos
        super().save(*args, **kwargs)


class ContenidoMultimediaServicio(models.Model):
    class Tipo(models.TextChoices):
        FOTO = 'FOTO', 'Foto'
        VIDEO = 'VIDEO', 'Video'

    EXTENSIONES = {
        Tipo.FOTO: {'.jpg', '.jpeg', '.png', '.webp'},
        Tipo.VIDEO: {'.mp4', '.mov', '.webm'},
    }

    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        related_name='multimedia'
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    archivo = models.FileField(upload_to='servicios/multimedia/')
    descripcion = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'contenido multimedia'
        verbose_name_plural = 'contenidos multimedia'

    def clean(self):
        permitidas = self.EXTENSIONES.get(self.tipo, set())
        if self.archivo and Path(self.archivo.name).suffix.lower() not in permitidas:
            raise ValidationError({
                'archivo': f"Extensión no válida para {self.tipo}. Permitidas: {', '.join(sorted(permitidas))}."
            })

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.servicio.nombre}"


class ElementoServicio(models.Model):
    class Tipo(models.TextChoices):
        PRODUCTO = 'PRODUCTO', 'Producto'
        INSUMO = 'INSUMO', 'Insumo'
        EQUIPO = 'EQUIPO', 'Equipo'

    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        related_name='elementos'
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    nombre = models.CharField(max_length=100)
    especificaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'elemento del servicio'
        verbose_name_plural = 'elementos del servicio'

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"
