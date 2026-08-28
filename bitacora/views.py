from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from usuarios.permissions import IsAdmin

from .models import Bitacora
from .serializers import BitacoraSerializer


class BitacoraPagination(PageNumberPagination):

    page_size = 50

    max_page_size = 200


class BitacoraView(APIView):

    permission_classes = [
        IsAdmin
    ]

    def get(self, request):

        registros = (
            Bitacora.objects
            .select_related("usuario")
            .all()
        )

        paginator = BitacoraPagination()

        pagina = paginator.paginate_queryset(
            registros,
            request
        )

        serializer = BitacoraSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )