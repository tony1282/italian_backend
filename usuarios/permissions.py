from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):

    message = "No tienes permisos de administrador."

    def has_permission(self, request, view):

        return (
            request.user
            and request.user.is_authenticated
            and request.user.rol == 1
            and request.user.activo
        )