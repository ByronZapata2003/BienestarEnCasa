from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from catalogo.serializers import ServicioSerializer

from .models import Direccion, PerfilProveedor, PerfilUsuario, ZonaAtencion


Usuario = get_user_model()


class RegistroSerializer(serializers.Serializer):
    nombres = serializers.CharField(max_length=150)
    apellidos = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmacion = serializers.CharField(write_only=True, trim_whitespace=False)
    rol = serializers.ChoiceField(choices=PerfilUsuario.Rol.choices)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        email = value.lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirmacion']:
            raise serializers.ValidationError({'password_confirmacion': 'Las contraseñas no coinciden.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password_confirmacion')
        password = validated_data.pop('password')
        rol = validated_data.pop('rol')
        telefono = validated_data.pop('telefono', '')
        email = validated_data.pop('email')
        usuario = Usuario.objects.create_user(
            username=email,
            email=email,
            first_name=validated_data['nombres'],
            last_name=validated_data['apellidos'],
            password=password,
        )
        return PerfilUsuario.objects.create(usuario=usuario, rol=rol, telefono=telefono)


class PerfilSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='usuario.email', read_only=True)
    nombres = serializers.CharField(source='usuario.first_name', read_only=True)
    apellidos = serializers.CharField(source='usuario.last_name', read_only=True)

    class Meta:
        model = PerfilUsuario
        fields = ('id', 'email', 'nombres', 'apellidos', 'rol', 'telefono', 'creado_en', 'actualizado_en')
        read_only_fields = ('id', 'rol', 'creado_en', 'actualizado_en')

class ActualizarPerfilSerializer(serializers.ModelSerializer):
    nombres = serializers.CharField(
        source='usuario.first_name',
        max_length=150,
        required=False,
    )
    apellidos = serializers.CharField(
        source='usuario.last_name',
        max_length=150,
        required=False,
    )

    class Meta:
        model = PerfilUsuario
        fields = ('nombres', 'apellidos', 'telefono')

    def update(self, instance, validated_data):
        datos_usuario = validated_data.pop('usuario', {})

        for campo, valor in datos_usuario.items():
            setattr(instance.usuario, campo, valor)

        if datos_usuario:
            instance.usuario.save(update_fields=list(datos_usuario.keys()))

        return super().update(instance, validated_data)

class InicioSesionSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        try:
            usuario = Usuario.objects.get(email__iexact=attrs['email'].lower())
        except Usuario.DoesNotExist:
            raise AuthenticationFailed('Correo o contraseña incorrectos.')

        usuario = authenticate(username=usuario.username, password=attrs['password'])
        if usuario is None or not usuario.is_active:
            raise AuthenticationFailed('Correo o contraseña incorrectos.')

        refresh = self.get_token(usuario)
        return {'refresh': str(refresh), 'access': str(refresh.access_token)}


class CerrarSesionSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def save(self, **kwargs):
        try:
            RefreshToken(self.validated_data['refresh']).blacklist()
        except Exception as error:
            raise serializers.ValidationError({'refresh': 'El token de actualización no es válido.'}) from error

class DireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direccion
        fields = (
            'id',
            'direccion',
            'ciudad',
            'barrio_sector',
            'informacion_complementaria',
            'es_principal',
            'creada_en',
            'actualizada_en',
        )
        read_only_fields = ('id', 'creada_en', 'actualizada_en')

class PerfilProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilProveedor
        fields = (
            'id',
            'descripcion_profesional',
            'creado_en',
            'actualizado_en',
        )
        read_only_fields = ('id', 'creado_en', 'actualizado_en')


class ZonaAtencionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZonaAtencion
        fields = ('id', 'ciudad', 'barrio_sector')
        read_only_fields = ('id',)


class ProveedorPublicoSerializer(serializers.ModelSerializer):
    nombres = serializers.CharField(source='perfil_usuario.usuario.first_name', read_only=True)
    apellidos = serializers.CharField(source='perfil_usuario.usuario.last_name', read_only=True)
    zonas_atencion = ZonaAtencionSerializer(many=True, read_only=True)
    servicios = ServicioSerializer(many=True, read_only=True)

    class Meta:
        model = PerfilProveedor
        fields = (
            'id',
            'nombres',
            'apellidos',
            'descripcion_profesional',
            'zonas_atencion',
            'servicios',
        )
