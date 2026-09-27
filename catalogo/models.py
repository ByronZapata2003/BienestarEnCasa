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
            self.duracion_historica = self.servicio.duracion
        super().save(*args, **kwargs)
        

class InsumoEquipo(models.Model):
    class Tipo(models.TextChoices):
        INSUMO = 'INSUMO', 'Insumo'
        EQUIPO = 'EQUIPO', 'Equipo'

    servicio = models.ForeignKey(
        Servicio, 
        on_delete=models.CASCADE, 
        related_name='insumos_equipos'
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.INSUMO)

    class Meta:
        verbose_name = 'insumo o equipo'
        verbose_name_plural = 'insumos y equipos'

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class MultimediaServicio(models.Model):
    class Tipo(models.TextChoices):
        IMAGEN = 'IMAGEN', 'Imagen'
        VIDEO = 'VIDEO', 'Video'

    servicio = models.ForeignKey(
        Servicio, 
        on_delete=models.CASCADE, 
        related_name='multimedia'
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    url_o_archivo = models.CharField(max_length=255, help_text="URL o ruta del archivo")

    class Meta:
        verbose_name = 'contenido multimedia'
        verbose_name_plural = 'contenidos multimedia'

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.servicio.nombre}"