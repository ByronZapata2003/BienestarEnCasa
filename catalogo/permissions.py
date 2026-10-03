from rest_framework import permissions
from usuarios.models import PerfilUsuario
from rest_framework import permissions

class IsProviderOwner(permissions.BasePermission):
    """
    Permite el acceso solo al proveedor dueño del servicio.
    Asume que la instancia del servicio tiene un campo 'proveedor' vinculado al usuario.
    """
    def has_object_permission(self, request, view, obj):
        # Asegura que el usuario autenticado sea el dueño del servicio
        return obj.proveedor.perfil_usuario.usuario == request.user

class IsProveedor(permissions.BasePermission):
    """
    Verifica que el usuario autenticado sea un Proveedor con perfil activo.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return hasattr(request.user, 'perfil') and request.user.perfil.rol == PerfilUsuario.Rol.PROVEEDOR


class IsProveedorOwnerOrReadOnly(permissions.BasePermission):
    
    message = 'Solo los proveedores pueden modificar el catálogo de servicios.'

    def has_permission(self, request, view):
        # Rechaza escrituras de clientes antes de validar el cuerpo de la petición
        if request.method in permissions.SAFE_METHODS:
            return True
        perfil = getattr(request.user, 'perfil', None)
        return perfil is not None and perfil.rol == PerfilUsuario.Rol.PROVEEDOR

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        servicio = getattr(obj, 'servicio', obj)
        return es_dueno_servicio(request.user, servicio)


def es_dueno_servicio(user, servicio):
    perfil = getattr(user, 'perfil', None)
    return (
        perfil is not None
        and hasattr(perfil, 'perfil_profesional')
        and servicio.proveedor_id == perfil.perfil_profesional.id
    )