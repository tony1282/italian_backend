import uuid

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .services import generar_ticket
from .serializers import TicketSerializer

from ventas.models import Venta
from usuarios.permissions import (
    ROL_SUPERADMIN,
    ROL_ADMIN,
    ROL_EMPLEADO,
)


class TicketVentaView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request, id):

        # =========================================================
        # 1. VALIDAR PERMISOS ANTES DE VALIDAR EL ID
        # =========================================================
        #
        # Un empleado no debe poder obtener información sobre
        # ventas ajenas, inexistentes o identificadores inválidos.
        #
        # Por seguridad, cualquier solicitud de un empleado que
        # llegue a este endpoint se rechaza aquí.
        #
        # La validación de propiedad se hará después de obtener
        # una venta válida.
        #
        # Para un empleado, si el ID es inválido, también se
        # responderá con 403, evitando revelar información.
        # =========================================================

        if request.user.rol == ROL_EMPLEADO:

            try:
                venta_id = uuid.UUID(
                    str(id)
                )
            except (
                ValueError,
                TypeError,
                AttributeError
            ):
                return Response(
                    {
                        "success": False,
                        "message": "No tienes permisos para consultar tickets.",
                        "data": None
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            try:
                venta = (
                    Venta.objects
                    .select_related(
                        "usuario",
                        "metodo_pago"
                    )
                    .prefetch_related(
                        "detalles__variante__producto"
                    )
                    .get(
                        id=venta_id
                    )
                )
            except Venta.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": "No tienes permisos para consultar tickets.",
                        "data": None
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            if venta.usuario_id != request.user.id:
                return Response(
                    {
                        "success": False,
                        "message": "No tienes permisos para consultar tickets.",
                        "data": None
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        # =========================================================
        # 2. ADMIN / SUPERADMIN
        # =========================================================

        elif request.user.rol in (
            ROL_ADMIN,
            ROL_SUPERADMIN
        ):

            try:
                venta_id = uuid.UUID(
                    str(id)
                )
            except (
                ValueError,
                TypeError,
                AttributeError
            ):
                return Response(
                    {
                        "success": False,
                        "message": "El identificador de la venta no es válido.",
                        "data": None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                venta = (
                    Venta.objects
                    .select_related(
                        "usuario",
                        "metodo_pago"
                    )
                    .prefetch_related(
                        "detalles__variante__producto"
                    )
                    .get(
                        id=venta_id
                    )
                )
            except Venta.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": "La venta no existe.",
                        "data": None
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

        # =========================================================
        # 3. CUALQUIER OTRO ROL
        # =========================================================

        else:
            return Response(
                {
                    "success": False,
                    "message": "No tienes permisos para consultar tickets.",
                    "data": None
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # =========================================================
        # 4. GENERAR TICKET
        # =========================================================

        data = generar_ticket(
            venta
        )

        serializer = TicketSerializer(
            data
        )

        return Response(
            {
                "success": True,
                "message": "Ticket generado correctamente.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )