import logging

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import MovimientoInventario
from .serializers import MovimientoInventarioSerializer
from .services import registrar_entrada, registrar_salida, registrar_ajuste

from usuarios.permissions import IsAdmin
from config.exceptions import BusinessException

logger = logging.getLogger(__name__)


class MovimientoInventarioViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = (
        MovimientoInventario.objects
        .select_related("variante", "variante__producto", "usuario")
        .all()
        .order_by("-fecha")
    )

    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsAuthenticated]

    # ==========================================================
    # ENTRADA
    # ==========================================================

    @action(detail=False, methods=["post"], permission_classes=[IsAdmin])
    def entrada(self, request):
        try:
            (
                movimiento,
                stock_anterior,
                stock_nuevo,
                stock_defectuoso_anterior,
                stock_defectuoso_nuevo,
            ) = registrar_entrada(
                variante_id=request.data.get("variante_id"),
                cantidad=request.data.get("cantidad"),
                observaciones=request.data.get("observaciones"),
                usuario=request.user,
            )
        except BusinessException as e:
            return Response(
                {"success": False, "message": str(e), "data": e.data},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Error inesperado en entrada de inventario")
            return Response(
                {"success": False, "message": "Error interno del servidor.", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Movimiento de inventario registrado correctamente.",
                "data": {
                    "id": movimiento.id,
                    "tipo": movimiento.tipo,
                    "stock_anterior": stock_anterior,
                    "cantidad": movimiento.cantidad,
                    "stock_nuevo": stock_nuevo,
                    "stock_defectuoso_anterior": stock_defectuoso_anterior,
                    "stock_defectuoso_nuevo": stock_defectuoso_nuevo,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    # ==========================================================
    # SALIDA
    # ==========================================================

    @action(detail=False, methods=["post"], permission_classes=[IsAdmin])
    def salida(self, request):
        try:
            (
                movimiento,
                stock_anterior,
                stock_nuevo,
                stock_defectuoso_anterior,
                stock_defectuoso_nuevo,
            ) = registrar_salida(
                variante_id=request.data.get("variante_id"),
                cantidad=request.data.get("cantidad"),
                observaciones=request.data.get("observaciones"),
                usuario=request.user,
            )
        except BusinessException as e:
            return Response(
                {"success": False, "message": str(e), "data": e.data},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Error inesperado en salida de inventario")
            return Response(
                {"success": False, "message": "Error interno del servidor.", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Movimiento de inventario registrado correctamente.",
                "data": {
                    "id": movimiento.id,
                    "tipo": movimiento.tipo,
                    "stock_anterior": stock_anterior,
                    "cantidad": movimiento.cantidad,
                    "stock_nuevo": stock_nuevo,
                    "stock_defectuoso_anterior": stock_defectuoso_anterior,
                    "stock_defectuoso_nuevo": stock_defectuoso_nuevo,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    # ==========================================================
    # AJUSTE
    # ==========================================================

    @action(detail=False, methods=["post"], permission_classes=[IsAdmin])
    def ajuste(self, request):
        try:
            (
                movimiento,
                stock_anterior,
                stock_nuevo,
                stock_defectuoso_anterior,
                stock_defectuoso_nuevo,
                tipo_ajuste,
            ) = registrar_ajuste(
                variante_id=request.data.get("variante_id"),
                stock_nuevo_solicitado=request.data.get("stock_nuevo"),
                observaciones=request.data.get("observaciones"),
                usuario=request.user,
            )
        except BusinessException as e:
            return Response(
                {"success": False, "message": str(e), "data": e.data},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Error inesperado en ajuste de inventario")
            return Response(
                {"success": False, "message": "Error interno del servidor.", "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Ajuste de inventario registrado correctamente.",
                "data": {
                    "id": movimiento.id,
                    "tipo": movimiento.tipo,
                    "stock_anterior": stock_anterior,
                    "cantidad": movimiento.cantidad,
                    "stock_nuevo": stock_nuevo,
                    "stock_defectuoso_anterior": stock_defectuoso_anterior,
                    "stock_defectuoso_nuevo": stock_defectuoso_nuevo,
                    "tipo_ajuste": tipo_ajuste,
                },
            },
            status=status.HTTP_201_CREATED,
        )