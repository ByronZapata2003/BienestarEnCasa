from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Categoria, Servicio, ContenidoMultimediaServicio, ElementoServicio

class ServicioUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        # Incluye los campos que el proveedor tiene permitido modificar, incluyendo el estado
        fields = ['id', 'nombre', 'descripcion', 'precio', 'duracion_minutos', 'estado']
        read_only_fields = ['id'] # Protege el ID de modificaciones

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion']


class ElementoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElementoServicio
        fields = ['id', 'servicio', 'tipo', 'nombre', 'especificaciones']


class ContenidoMultimediaServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContenidoMultimediaServicio
        fields = ['id', 'servicio', 'tipo', 'archivo', 'descripcion']

    def validate(self, attrs):
        # Usa la validación de extensión del modelo también en actualizaciones parciales
        contenido = ContenidoMultimediaServicio(
            tipo=attrs.get('tipo', getattr(self.instance, 'tipo', None)),
            archivo=attrs.get('archivo', getattr(self.instance, 'archivo', None)),
        )
        try:
            contenido.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict)
        return attrs


class ServicioSerializer(serializers.ModelSerializer):
    elementos = ElementoServicioSerializer(many=True, read_only=True)
    multimedia = ContenidoMultimediaServicioSerializer(many=True, read_only=True)
    categoria_detalle = CategoriaSerializer(source='categoria', read_only=True)
    nombre_proveedor = serializers.SerializerMethodField()

    class Meta:
        model = Servicio
        fields = [
            'id', 'proveedor', 'nombre_proveedor', 'categoria', 'categoria_detalle',
            'nombre', 'descripcion', 'duracion_minutos', 'precio', 'estado',
            'elementos', 'multimedia', 'creado_en', 'actualizado_en'
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
