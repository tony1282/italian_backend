import uuid
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from usuarios.permissions import IsAdmin

from .models import Bitacora
from .serializers import BitacoraSerializer


class BitacoraPagination(PageNumberPagination):

    page_size = 50
    page_size_query_param = "page_size"
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
            .order_by("-fecha")
        )

        # ------------------------------------------------------
        # FILTRO OPCIONAL ?usuario=<UUID>
        # ------------------------------------------------------

        usuario_id = request.query_params.get("usuario")

        if usuario_id:

            try:
                uuid.UUID(str(usuario_id))

            except (ValueError, TypeError, AttributeError):

                return Response(
                    {
                        "success": False,
                        "message": (
                            "El identificador de usuario "
                            "no es válido."
                        )
                    },
                    status=400
                )

            registros = registros.filter(
                usuario_id=usuario_id
            )

        # ------------------------------------------------------
        # FILTRO OPCIONAL ?modulo=Ventas
        # ------------------------------------------------------

        modulo = request.query_params.get("modulo")

        if modulo:

            registros = registros.filter(
                modulo__iexact=modulo
            )

        # ------------------------------------------------------
        # FILTRO OPCIONAL ?accion=CANCELAR_VENTA
        # ------------------------------------------------------

        accion = request.query_params.get("accion")

        if accion:

            registros = registros.filter(
                accion__iexact=accion
            )

        # ------------------------------------------------------
        # FILTROS DE FECHA
        # ------------------------------------------------------

        fecha_desde = request.query_params.get(
            "fecha_desde"
        )

        fecha_hasta = request.query_params.get(
            "fecha_hasta"
        )

        fecha_desde_obj = None
        fecha_hasta_obj = None

        # ------------------------------------------------------
        # VALIDAR fecha_desde
        # ------------------------------------------------------

        if fecha_desde:

            try:
                fecha_desde_obj = datetime.strptime(
                    fecha_desde,
                    "%Y-%m-%d"
                ).date()

            except (ValueError, TypeError):

                return Response(
                    {
                        "success": False,
                        "message": (
                            "La fecha_desde no es válida. "
                            "Use el formato YYYY-MM-DD."
                        )
                    },
                    status=400
                )

        # ------------------------------------------------------
        # VALIDAR fecha_hasta
        # ------------------------------------------------------

        if fecha_hasta:

            try:
                fecha_hasta_obj = datetime.strptime(
                    fecha_hasta,
                    "%Y-%m-%d"
                ).date()

            except (ValueError, TypeError):

                return Response(
                    {
                        "success": False,
                        "message": (
                            "La fecha_hasta no es válida. "
                            "Use el formato YYYY-MM-DD."
                        )
                    },
                    status=400
                )

        # ------------------------------------------------------
        # VALIDAR RANGO
        # ------------------------------------------------------

        if (
            fecha_desde_obj
            and fecha_hasta_obj
            and fecha_desde_obj > fecha_hasta_obj
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "La fecha_desde no puede ser "
                        "mayor que fecha_hasta."
                    )
                },
                status=400
            )

        # ------------------------------------------------------
        # APLICAR fecha_desde
        # ------------------------------------------------------

        if fecha_desde_obj:

            registros = registros.filter(
                fecha__date__gte=fecha_desde_obj
            )

        # ------------------------------------------------------
        # APLICAR fecha_hasta
        # ------------------------------------------------------

        if fecha_hasta_obj:

            registros = registros.filter(
                fecha__date__lte=fecha_hasta_obj
            )

        # ------------------------------------------------------
        # PAGINACIÓN
        # ------------------------------------------------------

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