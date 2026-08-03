from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import generar_ticket
from .serializers import TicketSerializer

from ventas.models import Venta


class TicketVentaView(APIView):

    def get(self, request, id):

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