from rest_framework import permissions
from usuarios.models import PerfilUsuario


def _es_propietario_del_servicio(user, obj):
    servicio = obj if hasattr(obj, 'proveedor') else getattr(obj, 'servicio', None)
    proveedor = getattr(servicio, 'proveedor', None)
    perfil_proveedor = getattr(proveedor, 'perfil_usuario', None)
    return bool(perfil_proveedor and perfil_proveedor.usuario_id == user.pk)


class IsProviderOwner(permissions.BasePermission):
    """
    Permite el acceso solo al proveedor dueño del servicio.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        return _es_propietario_del_servicio(request.user, obj)


class IsProveedor(permissions.BasePermission):
    """
    Verifica que el usuario autenticado sea un Proveedor con perfil activo.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff or request.user.is_superuser:
            return True

        perfil = getattr(request.user, 'perfil', None)
        if perfil is not None:
            return str(getattr(perfil, 'rol', '')).upper() in ['PROVEEDOR', 'PRO']
        return False


class IsProveedorOwnerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Lectura permitida a cualquiera
        if request.method in permissions.SAFE_METHODS:
            return True

        # Para modificar/eliminar debe estar autenticado
        if not request.user or not request.user.is_authenticated:
            return False

        # Si es admin o staff, tiene acceso total
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Verificar rol de proveedor
        perfil = getattr(request.user, 'perfil', None)
        if perfil is not None:
            return str(getattr(perfil, 'rol', '')).upper() in ['PROVEEDOR', 'PRO']

        return False

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.is_staff or request.user.is_superuser:
            return True

        return _es_propietario_del_servicio(request.user, obj)


def es_dueno_servicio(user, servicio):
    """
    Función auxiliar para validar si un usuario es dueño de un servicio o tiene rol de proveedor.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True

    return _es_propietario_del_servicio(user, servicio)
