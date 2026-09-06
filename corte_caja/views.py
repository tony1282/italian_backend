import logging
import uuid

from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import CorteCaja, MovimientoCaja
from .serializers import CorteCajaSerializer, MovimientoCajaSerializer
from .services import abrir_caja, cerrar_caja

from config.exceptions import BusinessException

logger = logging.getLogger(__name__)


class CorteCajaPagination(PageNumberPagination):
    page_size = 50
    max_page_size = 200


def _validar_uuid(valor, mensaje="El identificador no es un UUID válido."):
    try:
        uuid.UUID(str(valor))
    except (ValueError, TypeError, AttributeError):
        return Response(
            {"success": False, "message": mensaje},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def _ejecutar_servicio(fn, log_msg):
    try:
        return fn(), None
    except BusinessException as e:
        return None, Response(
            {"success": False, "message": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        logger.exception(log_msg)
        return None, Response(
            {"success": False, "message": "Error interno del servidor."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class CorteCajaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):

    queryset = CorteCaja.objects.none()
    serializer_class = CorteCajaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CorteCajaPagination

    def get_queryset(self):
        qs = (
            CorteCaja.objects
            .select_related("caja", "usuario")
            .order_by("-fecha_inicio")
        )

        if self.request.user.rol not in (0, 1):
            qs = qs.filter(usuario=self.request.user)

        return qs

    # ==========================================================
    # ABRIR CAJA
    # ==========================================================

    @action(detail=False, methods=["post"], url_path="abrir")
    def abrir(self, request):
        resultado, error = _ejecutar_servicio(
            lambda: abrir_caja(
                caja_id=request.data.get("caja_id"),
                efectivo_inicial_raw=request.data.get("efectivo_inicial"),
                usuario=request.user,
            ),
            "Error inesperado en abrir_caja",
        )

        if error:
            return error

        return Response(
            {
                "success": True,
                "message": "Caja abierta correctamente.",
                "data": {
                    "corte_id": resultado.id,
                    "fecha_inicio": resultado.fecha_inicio,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    # ==========================================================
    # CERRAR CAJA
    # ==========================================================

    @action(detail=False, methods=["post"], url_path="cerrar")
    def cerrar(self, request):
        resultado, error = _ejecutar_servicio(
            lambda: cerrar_caja(
                caja_id=request.data.get("caja_id"),
                efectivo_final_raw=request.data.get("efectivo_final"),
                usuario=request.user,
            ),
            "Error inesperado en cerrar_caja",
        )

        if error:
            return error

        corte, efectivo_esperado, diferencia = resultado

        return Response(
            {
                "success": True,
                "message": "Caja cerrada correctamente.",
                "data": {
                    "corte_id": corte.id,
                    "efectivo_esperado": efectivo_esperado,
                    "efectivo_contado": corte.efectivo_final,
                    "diferencia": diferencia,
                },
            },
            status=status.HTTP_200_OK,
        )

    # ==========================================================
    # CORTE ACTIVO
    # ==========================================================

    @action(detail=False, methods=["get"], url_path="corte/activo")
    def activo(self, request):
        caja_id = request.query_params.get("caja_id")

        if not caja_id:
            return Response(
                {
                    "success": False,
                    "message": "El parámetro caja_id es obligatorio.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        error = _validar_uuid(
            caja_id,
            "El parámetro caja_id no es un UUID válido."
        )

        if error:
            return error

        corte = (
            self.get_queryset()
            .filter(
                caja_id=caja_id,
                fecha_fin__isnull=True
            )
            .first()
        )

        if not corte:
            return Response(
                {
                    "success": False,
                    "message": "No existe un corte abierto para esta caja.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                "data": self.get_serializer(corte).data,
            },
            status=status.HTTP_200_OK,
        )

    # ==========================================================
    # HISTORIAL DE CORTES
    # ==========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path=r"cajas/(?P<caja_id>[^/.]+)/cortes"
    )
    def historial(self, request, caja_id):
        error = _validar_uuid(
            caja_id,
            "El identificador de la caja no es un UUID válido."
        )

        if error:
            return error

        cortes = self.get_queryset().filter(
            caja_id=caja_id
        )

        paginator = CorteCajaPagination()

        pagina = paginator.paginate_queryset(
            cortes,
            request
        )

        return paginator.get_paginated_response(
            self.get_serializer(
                pagina,
                many=True
            ).data
        )

    # ==========================================================
    # MOVIMIENTOS DE CAJA
    # ==========================================================

    @action(
        detail=True,
        methods=["get"],
        url_path="movimientos"
    )
    def movimiento(self, request, pk=None):

        error = _validar_uuid(
            pk,
            "El identificador del corte no es un UUID válido."
        )

        if error:
            return error

        try:
            corte = self.get_queryset().get(
                pk=pk
            )

        except CorteCaja.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "El corte de caja no existe.",
                    "data": None,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        movimientos = (
            MovimientoCaja.objects
            .select_related(
                "metodo_pago",
                "usuario",
                "devolucion"
            )
            .filter(
                corte_caja=corte
            )
            .order_by("-fecha")
        )

        return Response(
            {
                "success": True,
                "data": MovimientoCajaSerializer(
                    movimientos,
                    many=True
                ).data,
            },
            status=status.HTTP_200_OK,
        )