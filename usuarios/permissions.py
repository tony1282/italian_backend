from rest_framework.permissions import BasePermission


ROL_SUPERADMIN = 0
ROL_ADMIN = 1
ROL_EMPLEADO = 2


class IsAdmin(BasePermission):

    message = "No tienes permisos de administrador."

    def has_permission(self, request, view):

        return (
            request.user
            and request.user.is_authenticated
            and request.user.rol in (ROL_SUPERADMIN, ROL_ADMIN)
            and request.user.activo
        )


class IsSuperAdmin(BasePermission):

    message = "No tienes permisos de superadministrador."

    def has_permission(self, request, view):

        return (
            request.user
            and request.user.is_authenticated
            and request.user.rol == ROL_SUPERADMIN
            and request.user.activo
        )