from rest_framework import serializers
from .models import SolicitudReserva

class SolicitudReservaSerializer(serializers.ModelSerializer):
    nombre_proveedor = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudReserva
        fields = [
            'id', 'cliente', 'proveedor', 'nombre_proveedor', 'servicio',
            'nombre_servicio_copia', 'precio_copia', 'duracion_minutos_copia',
            'fecha_solicitada', 'hora_solicitada', 'direccion_atencion',
            'barrio_sector', 'informacion_complementaria', 'observaciones',
            'estado', 'motivo_rechazo_cancelacion', 'creado_en', 'actualizado_en'
        ]
        read_only_fields = [
            'cliente', 'nombre_servicio_copia', 'precio_copia',
            'duracion_minutos_copia', 'estado', 'motivo_rechazo_cancelacion',
            'creado_en', 'actualizado_en'
        ]

    def get_nombre_proveedor(self, obj):
        u = obj.proveedor.perfil_usuario.usuario
        return f"{u.first_name} {u.last_name}".strip() or u.email

    def create(self, validated_data):
        servicio = validated_data.get('servicio')
        # Guardar copia fija de las condiciones del servicio al crear (RF-23)
        validated_data['nombre_servicio_copia'] = servicio.nombre
        validated_data['precio_copia'] = servicio.precio
        validated_data['duracion_minutos_copia'] = servicio.duracion_minutos
        return super().create(validated_data)