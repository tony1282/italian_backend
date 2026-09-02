import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from usuarios.permissions import IsAdmin
from config.exceptions import BusinessException

from .models import Garantia
from .serializers import (
    CrearGarantiaSerializer,
    AprobarGarantiaSerializer,
    RechazarGarantiaSerializer,
    FinalizarGarantiaSerializer,
    GarantiaSerializer,
)
from .services import (
    crear_garantia,
    aprobar_garantia,
    rechazar_garantia,
    finalizar_garantia,
)


class GarantiaPagination(PageNumberPagination):

    page_size = 50

    max_page_size = 200


class GarantiaListCreateView(APIView):

    permission_classes = [IsAuthenticated]

    # GET /api/garantias/
    def get(self, request):

        garantias = Garantia.objects.select_related(
            "venta",
            "detalle_venta",
            "variante",
            "variante__producto",
            "usuario",
            "variante_nueva"
        ).all()

        paginator = GarantiaPagination()

        pagina = paginator.paginate_queryset(
            garantias,
            request
        )

        serializer = GarantiaSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )

    # POST /api/garantias/
    def post(self, request):

        serializer = CrearGarantiaSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            garantia = crear_garantia(
                serializer.validated_data,
                request.user
            )

            return Response(
                {
                    "success": True,
                    "message": "Garantía registrada correctamente.",
                    "data": GarantiaSerializer(garantia).data
                },
                status=status.HTTP_201_CREATED
            )

        except BusinessException as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception:

            logging.getLogger(__name__).exception(
                "Error inesperado en crear_garantia"
            )

            return Response(
                {
                    "success": False,
                    "message": "Error interno del servidor."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GarantiaDetailView(APIView):

    permission_classes = [IsAuthenticated]

    # GET /api/garantias/<id>/
    def get(self, request, id):

        try:

            garantia = (
                Garantia.objects
                .select_related(
                    "venta",
                    "detalle_venta",
                    "variante",
                    "variante__producto",
                    "usuario",
                    "variante_nueva"
                )
                .get(id=id)
            )

        except Garantia.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "La garantía no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "success": True,
                "data": GarantiaSerializer(garantia).data
            },
            status=status.HTTP_200_OK
        )

    # PUT /api/garantias/<id>/
    def put(self, request, id):

        try:

            garantia = Garantia.objects.get(
                id=id
            )

        except Garantia.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "La garantía no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Solo se pueden modificar garantías pendientes
        if garantia.estado != "PENDIENTE":

            return Response(
                {
                    "success": False,
                    "message": (
                        "Solo se pueden modificar "
                        "garantías pendientes."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ========================================================
        # Solo se permite modificar el motivo
        # ========================================================

        campos_permitidos = {
            "motivo"
        }

        campos_recibidos = set(
            request.data.keys()
        )

        campos_no_permitidos = (
            campos_recibidos - campos_permitidos
        )

        if campos_no_permitidos:

            campo = next(
                iter(campos_no_permitidos)
            )

            return Response(
                {
                    "success": False,
                    "message": (
                        f"El campo '{campo}' "
                        "no puede modificarse."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ========================================================
        # Validar motivo
        # ========================================================

        if "motivo" not in request.data:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El campo 'motivo' "
                        "es obligatorio."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        motivo = request.data["motivo"]

        if not isinstance(motivo, str) or not motivo.strip():

            return Response(
                {
                    "success": False,
                    "message": (
                        "El motivo no puede estar vacío."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ========================================================
        # Actualizar
        # ========================================================

        garantia.motivo = motivo.strip()

        garantia.save(
            update_fields=[
                "motivo",
                "fecha_actualizacion"
            ]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Garantía actualizada correctamente."
                ),
                "data": GarantiaSerializer(
                    garantia
                ).data
            },
            status=status.HTTP_200_OK
        )


class GarantiaAprobarView(APIView):

    permission_classes = [IsAdmin]

    # POST /api/garantias/<id>/aprobar/
    def post(self, request, id):

        serializer = AprobarGarantiaSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            garantia = aprobar_garantia(
                id,
                serializer.validated_data,
                request.user
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Garantía aprobada correctamente."
                    ),
                    "data": GarantiaSerializer(
                        garantia
                    ).data
                },
                status=status.HTTP_200_OK
            )

        except BusinessException as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception:

            logging.getLogger(__name__).exception(
                "Error inesperado en aprobar_garantia"
            )

            return Response(
                {
                    "success": False,
                    "message": "Error interno del servidor."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GarantiaRechazarView(APIView):

    permission_classes = [IsAdmin]

    # POST /api/garantias/<id>/rechazar/
    def post(self, request, id):

        serializer = RechazarGarantiaSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            garantia = rechazar_garantia(
                id,
                serializer.validated_data,
                request.user
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Garantía rechazada correctamente."
                    ),
                    "data": GarantiaSerializer(
                        garantia
                    ).data
                },
                status=status.HTTP_200_OK
            )

        except BusinessException as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception:

            logging.getLogger(__name__).exception(
                "Error inesperado en rechazar_garantia"
            )

            return Response(
                {
                    "success": False,
                    "message": "Error interno del servidor."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GarantiaFinalizarView(APIView):

    permission_classes = [IsAdmin]

    # POST /api/garantias/<id>/finalizar/
    def post(self, request, id):

        serializer = FinalizarGarantiaSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            garantia = finalizar_garantia(
                id,
                serializer.validated_data,
                request.user
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Garantía finalizada correctamente."
                    ),
                    "data": GarantiaSerializer(
                        garantia
                    ).data
                },
                status=status.HTTP_200_OK
            )

        except BusinessException as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception:

            logging.getLogger(__name__).exception(
                "Error inesperado en finalizar_garantia"
            )

            return Response(
                {
                    "success": False,
                    "message": "Error interno del servidor."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )