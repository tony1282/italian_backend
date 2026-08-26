from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Bitacora
from .serializers import BitacoraSerializer


class BitacoraView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if request.user.rol != 1:
            return Response(
                {
                    "success": False,
                    "message": "No tienes permisos para consultar la bitácora."
                },
                status=403
            )

        registros = (
            Bitacora.objects
            .select_related("usuario")
            .all()
        )

        serializer = BitacoraSerializer(
            registros,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": "Registros de bitácora obtenidos correctamente.",
                "data": serializer.data
            }
        )