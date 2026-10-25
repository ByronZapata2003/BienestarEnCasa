from rest_framework.permissions import BasePermission

from .models import PerfilUsuario


class EsProveedorRegistrado(BasePermission):
    """Restringe la disponibilidad al proveedor autenticado de la propia cuenta."""

    message = 'Solo un proveedor registrado puede consultar o gestionar su disponibilidad.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False

        perfil = getattr(user, 'perfil', None)
        return bool(perfil and perfil.rol == PerfilUsuario.Rol.PROVEEDOR)
