from rest_framework.permissions import BasePermission


ROL_ADMINISTRADOR = 1


class EsAdministrador(BasePermission):

    message = "Solo un administrador puede realizar esta acción."

    def has_permission(self, request, view):

        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "rol", None) == ROL_ADMINISTRADOR
        )