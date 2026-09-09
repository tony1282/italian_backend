import logging

from django.db.models import Sum, IntegerField, Value
from django.db.models.functions import Coalesce

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from .models import Venta
from .serializers import VentaSerializer
from .services import crear_venta, cancelar_venta

from detalle_venta.models import DetalleVenta
from devoluciones.models import DetalleDevolucion
from garantias.models import Garantia

from config.exceptions import BusinessException

logger = logging.getLogger(__name__)


class VentaPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


def _usuario_activo(user):
    if not user.activo:
        return Response(
            {"success": False, "message": "El usuario está inactivo.", "data": None},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _ejecutar_servicio(fn, log_msg):
    try:
        return fn(), None
    except BusinessException as e:
        return None, Response(
            {"success": False, "message": str(e), "data": getattr(e, "data", None)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        logger.exception(log_msg)
        return None, Response(
            {"success": False, "message": "Error interno del servidor.", "data": None},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _construir_mapas(detalle_ids):
    devueltas_map = {
        str(r["detalle_venta_id"]): r["total"]
        for r in (
            DetalleDevolucion.objects
            .filter(
                detalle_venta_id__in=detalle_ids,
                devolucion__estado__in=["PENDIENTE", "APROBADA"],
            )
            .values("detalle_venta_id")
            .annotate(total=Coalesce(Sum("cantidad"), Value(0, output_field=IntegerField())))
        )
    }
    garantias_map = {
        str(r["detalle_venta_id"]): r["total"]
        for r in (
            Garantia.objects
            .filter(
                detalle_venta_id__in=detalle_ids,
                estado__in=["PENDIENTE", "APROBADA"],
            )
            .values("detalle_venta_id")
            .annotate(total=Coalesce(Sum("cantidad"), Value(0, output_field=IntegerField())))
        )
    }
    return devueltas_map, garantias_map


def _serializar_detalle(d, devueltas_map, garantias_map):
    return {
        "detalle_id": d.id,
        "producto": d.variante.producto.nombre,
        "variante": d.variante.nombre,
        "variante_id": d.variante.id,
        "cantidad": d.cantidad,
        "cantidad_disponible": max(
            d.cantidad - devueltas_map.get(str(d.id), 0) - garantias_map.get(str(d.id), 0), 0
        ),
        "precio_unitario": d.precio_unitario,
        "descuento": d.descuento,
        "subtotal": d.subtotal,
    }


def _serializar_venta(v):
    return {
        "id": v.id,
        "folio": v.folio,
        "fecha": v.fecha,
        "usuario": v.usuario.nombre,
        "metodo_pago": v.metodo_pago.nombre,
        "caja": v.corte_caja.caja.nombre,
        "subtotal": v.subtotal,
        "descuento": v.descuento,
        "iva": v.iva,
        "total": v.total,
        "estado": v.estado,
    }


class VentaViewSet(viewsets.ModelViewSet):

    queryset = Venta.objects.all()
    serializer_class = VentaSerializer
    http_method_names = ["get", "post", "head", "options"]
    pagination_class = VentaPagination

    def get_permissions(self):
        return [IsAuthenticated()]

    # ==========================================================
    # CREAR VENTA
    # ==========================================================

    def create(self, request, *args, **kwargs):
        error = _usuario_activo(request.user)
        if error:
            return error

        venta, err = _ejecutar_servicio(
            lambda: crear_venta(request.data, request.user),
            "Error inesperado en crear_venta",
        )
        if err:
            return err
        return Response(
            {
                "success": True,
                "folio": venta.folio,
                "venta_id": venta.id,
                "message": "Venta registrada correctamente.",
            },
            status=status.HTTP_201_CREATED,
        )

    # ==========================================================
    # LISTAR VENTAS
    # ==========================================================

    def list(self, request, *args, **kwargs):
        if request.user.rol in (0, 1):
            ventas = ( Venta.objects.select_related(
                "usuario",
                "metodo_pago",
                "corte_caja",
                "corte_caja__caja"
                ).all()
            )
        else:
            ventas = (
                Venta.objects.select_related(
                    "usuario",
                    "metodo_pago",
                    "corte_caja",
                    "corte_caja__caja"
                ).filter(
                    usuario=request.user
                )
            )    
        
       

        paginator = VentaPagination()

        pagina = paginator.paginate_queryset(
            ventas,
            request,
        )

        return paginator.get_paginated_response(
            {
                "success": True,
                "data": [_serializar_venta(v) for v in pagina],
            }
        )

    # ==========================================================
    # CONSULTAR VENTA
    # ==========================================================

    def retrieve(self, request, pk=None):
        
        queryset = (Venta.objects.select_related(
            "usuario",
            "metodo_pago",
            "corte_caja",
            "corte_caja__caja"
        ).prefetch_related(
            "detalles__variante__producto"
        )
        
        )
        
        
        try:
            if request.user.rol in (0,1):
                venta = queryset.get(
                    pk=pk,
                )
            else:
                venta = queryset.get(
                    pk=pk,
                    usuario=request.user
                )
        except (Venta.DoesNotExist, ValueError, TypeError):
            return Response(
                {
                    "success": False,
                    "message": "La venta no existe.",
                    "data": None
                },
                status=status.HTTP_404_NOT_FOUND, 
            )

        detalle_ids = [d.id for d in venta.detalles.all()]
        devueltas_map, garantias_map = _construir_mapas(detalle_ids)
        productos = [_serializar_detalle(d, devueltas_map, garantias_map) for d in venta.detalles.all()]

        return Response(
            {"success": True, "data": {**_serializar_venta(venta), "productos": productos}},
            status=status.HTTP_200_OK,
        )

    # ==========================================================
    # CANCELAR VENTA
    # ==========================================================

    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        error = _usuario_activo(request.user)
        if error:
            return error

        _, err = _ejecutar_servicio(
            lambda: cancelar_venta(pk, request.user),
            "Error inesperado en cancelar_venta",
        )
        if err:
            return err
        return Response(
            {"success": True, "message": "Venta cancelada correctamente.", "data": None},
            status=status.HTTP_200_OK,
        )