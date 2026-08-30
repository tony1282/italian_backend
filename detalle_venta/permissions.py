from rest_framework.permissions import BasePermission


ROL_ADMINISTRADOR = 1


class EsAdministrador(BasePermission):

    message = "Solo un administrador puede ver este detalle."

    def has_permission(self, request, view):

        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "rol", None) in (0, 1)
        )