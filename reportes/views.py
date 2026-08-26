from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .services import (
    reporte_ventas,
    reporte_productos,
    reporte_inventario,
    reporte_stock_bajo,
    reporte_cortes,
    reporte_devoluciones,
    reporte_garantias,
    reporte_movimientos,
)

from .serializers import (
    ReporteVentaSerializer,
    ReporteProductoSerializer,
    ReporteInventarioSerializer,
    ReporteStockBajoSerializer,
    ReporteCorteSerializer,
    ReporteDevolucionSerializer,
    ReporteGarantiaSerializer,
    ReporteMovimientoSerializer,
)


# ============================================================
# PERMISO
# ============================================================

def validar_admin(request):

    return request.user.rol == 1


# ============================================================
# REPORTE DE VENTAS
# ============================================================

class ReporteVentasView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if not validar_admin(request):

            return Response(
                {
                    "success": False,
                    "message": (
                        "No tienes permisos para "
                        "consultar este reporte."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        fecha_inicio = request.query_params.get(
            "fecha_inicio"
        )

        fecha_fin = request.query_params.get(
            "fecha_fin"
        )

        usuario_id = request.query_params.get(
            "usuario"
        )

        estado = request.query_params.get(
            "estado"
        )

        data = reporte_ventas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            usuario_id=usuario_id,
            estado=estado
        )

        serializer = ReporteVentaSerializer(
            data,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Reporte de ventas generado correctamente."
                ),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# PRODUCTOS MÁS VENDIDOS
# ============================================================

class ReporteProductosView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if not validar_admin(request):

            return Response(
                {
                    "success": False,
                    "message": (
                        "No tienes permisos para "
                        "consultar este reporte."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        data = reporte_productos()

        serializer = ReporteProductoSerializer(
            data,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Reporte de productos "
                    "generado correctamente."
                ),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# INVENTARIO
# ============================================================

class ReporteInventarioView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if not validar_admin(request):

            return Response(
                {
                    "success": False,
                    "message": (
                        "No tienes permisos para "
                        "consultar este reporte."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        data = reporte_inventario()

        serializer = ReporteInventarioSerializer(
            data,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Reporte de inventario "
                    "generado correctamente."
                ),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# STOCK BAJO
# ============================================================

class ReporteStockBajoView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if not validar_admin(request):

            return Response(
                {
                    "success": False,
                    "message": (
                        "No tienes permisos para "
                        "consultar este reporte."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        data = reporte_stock_bajo()

        serializer = ReporteStockBajoSerializer(
            data,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Reporte de stock bajo "
                    "generado correctamente."
                ),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# CORTES DE CAJA
# ============================================================

class ReporteCortesView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if not validar_admin(request):

            return Response(
                {
                    "success": False,
                    "message": (
                        "No tienes permisos para "
                        "consultar este reporte."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        data = reporte_cortes()

        serializer = ReporteCorteSerializer(
            data,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Reporte de cortes de caja "
                    "generado correctamente."
                ),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# DEVOLUCIONES
# ============================================================

class ReporteDevolucionesView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if not validar_admin(request):

            return Response(
                {
                    "success": False,
                    "message": (
                        "No tienes permisos para "
                        "consultar este reporte."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        data = reporte_devoluciones()

        serializer = ReporteDevolucionSerializer(
            data,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Reporte de devoluciones "
                    "generado correctamente."
                ),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# GARANTÍAS
# ============================================================

class ReporteGarantiasView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if not validar_admin(request):

            return Response(
                {
                    "success": False,
                    "message": (
                        "No tienes permisos para "
                        "consultar este reporte."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        data = reporte_garantias()

        serializer = ReporteGarantiaSerializer(
            data,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Reporte de garantías "
                    "generado correctamente."
                ),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# MOVIMIENTOS DE INVENTARIO
# ============================================================

class ReporteMovimientosView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        if not validar_admin(request):

            return Response(
                {
                    "success": False,
                    "message": (
                        "No tienes permisos para "
                        "consultar este reporte."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        data = reporte_movimientos()

        serializer = ReporteMovimientoSerializer(
            data,
            many=True
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Reporte de movimientos "
                    "generado correctamente."
                ),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )