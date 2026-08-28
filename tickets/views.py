import uuid

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .services import generar_ticket
from .serializers import TicketSerializer

from ventas.models import Venta


class TicketVentaView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request, id):

        try:

            uuid.UUID(
                str(id)
            )

        except (ValueError, TypeError, AttributeError):

            return Response(
                {
                    "success": False,
                    "message": "El identificador de la venta no es válido."
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        try:
            Venta.objects.get(
                id=id
            )

        except Venta.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "La venta no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )


        data = generar_ticket(id)


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