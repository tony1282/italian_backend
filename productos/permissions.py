from rest_framework.permissions import (
    BasePermission
)


class ProductoPermission(
    BasePermission
):

    message = (
        "No tienes permisos para modificar productos."
    )

    def has_permission(
        self,
        request,
        view
    ):

        if not (
            request.user
            and request.user.is_authenticated
            and request.user.activo
        ):
            return False

        # --------------------------------------------------
        # CONSULTA
        # --------------------------------------------------

        if request.method in [
            "GET",
            "HEAD",
            "OPTIONS"
        ]:

            return True

        # --------------------------------------------------
        # MODIFICACIÓN
        # SOLO ADMINISTRADOR
        # --------------------------------------------------

        return request.user.rol in (0, 1)