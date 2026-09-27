from rest_framework import serializers
from .models import Categoria, Servicio, InsumoEquipo, MultimediaServicio

class ServicioUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        # Incluye los campos que el proveedor tiene permitido modificar, incluyendo el estado
        fields = ['id', 'nombre', 'descripcion', 'precio', 'duracion', 'activo']
        read_only_fields = ['id'] # Protege el ID de modificaciones

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion']


class InsumoEquipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsumoEquipo
        fields = ['id', 'nombre', 'descripcion', 'tipo']


class MultimediaServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MultimediaServicio
        fields = ['id', 'tipo', 'url_o_archivo']


class ServicioSerializer(serializers.ModelSerializer):
    insumos_equipos = InsumoEquipoSerializer(many=True, read_only=True)
    multimedia = MultimediaServicioSerializer(many=True, read_only=True)
    categoria_detalle = CategoriaSerializer(source='categoria', read_only=True)
    nombre_proveedor = serializers.SerializerMethodField()

    class Meta:
        model = Servicio
        fields = [
            'id', 'proveedor', 'nombre_proveedor', 'categoria', 'categoria_detalle',
            'nombre', 'descripcion', 'duracion_minutos', 'precio', 'estado',
            'insumos_equipos', 'multimedia', 'creado_en', 'actualizado_en'
        ]
        read_only_fields = ['proveedor', 'creado_en', 'actualizado_en']

    def get_nombre_proveedor(self, obj):
        usuario = obj.proveedor.perfil_usuario.usuario
        return f"{usuario.first_name} {usuario.last_name}".strip() or usuario.email

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio del servicio debe ser mayor a 0.")
        return value

    def validate_duracion_minutos(self, value):
        if value <= 0:
            raise serializers.ValidationError("La duración debe ser al menos de 1 minuto.")
        return value