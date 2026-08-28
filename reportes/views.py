import uuid

from datetime import datetime

from rest_framework.views import APIView

from rest_framework.response import Response

from rest_framework.permissions import (
    IsAuthenticated
)

from rest_framework.pagination import (
    PageNumberPagination
)

from rest_framework import status

from usuarios.permissions import IsAdmin

from ventas.models import Venta

from inventario.models import MovimientoInventario

from garantias.models import Garantia


from .services import (
    reporte_resumen_dia,
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
    ReporteResumenDiaSerializer,
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
# PERMISOS
# ============================================================

PERMISSION_ADMIN = [
    IsAuthenticated,
    IsAdmin,
]

PERMISSION_EMPLEADO = [
    IsAuthenticated,
]


# ============================================================
# PAGINACIÓN
# ============================================================

class ReportePagination(
    PageNumberPagination
):

    page_size = 50

    max_page_size = 200


def _paginar(request, data):

    paginator = ReportePagination()

    pagina = paginator.paginate_queryset(
        data,
        request
    )

    return paginator, pagina


# ============================================================
# VALIDAR FECHA
# ============================================================

def _parsear_fecha(
    valor,
    nombre
):

    if not valor:

        return None, None

    try:

        fecha = datetime.strptime(
            valor,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return (
            None,
            Response(
                {
                    "success": False,
                    "message": (
                        f"{nombre} no es una fecha "
                        "válida (formato YYYY-MM-DD)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        )

    return fecha, None


# ============================================================
# VALIDAR RANGO
# ============================================================

def _validar_rango(
    fecha_inicio,
    fecha_fin
):

    if (
        fecha_inicio
        and fecha_fin
        and fecha_inicio > fecha_fin
    ):

        return Response(
            {
                "success": False,
                "message": (
                    "fecha_inicio no puede ser "
                    "posterior a fecha_fin."
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    return None


# ============================================================
# RESUMEN DEL DÍA
# ============================================================

class ReporteResumenDiaView(
    APIView
):

    permission_classes = PERMISSION_ADMIN

    def get(
        self,
        request
    ):

        fecha = request.query_params.get(
            "fecha"
        )

        if not fecha:

            from django.utils import timezone

            fecha = timezone.localdate()

        else:

            fecha, error = _parsear_fecha(
                fecha,
                "fecha"
            )

            if error:

                return error

        data = reporte_resumen_dia(
            fecha=fecha
        )

        serializer = (
            ReporteResumenDiaSerializer(
                data
            )
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


# ============================================================
# REPORTE DE VENTAS
# ============================================================

class ReporteVentasView(
    APIView
):

    permission_classes = PERMISSION_ADMIN

    def get(
        self,
        request
    ):

        fecha_inicio, error = _parsear_fecha(
            request.query_params.get(
                "fecha_inicio"
            ),
            "fecha_inicio"
        )

        if error:
            return error

        fecha_fin, error = _parsear_fecha(
            request.query_params.get(
                "fecha_fin"
            ),
            "fecha_fin"
        )

        if error:
            return error

        error_rango = _validar_rango(
            fecha_inicio,
            fecha_fin
        )

        if error_rango:
            return error_rango

        usuario_id = (
            request.query_params.get(
                "usuario"
            )
        )

        estado = (
            request.query_params.get(
                "estado"
            )
        )

        # ----------------------------------------------------
        # VALIDAR UUID USUARIO
        # ----------------------------------------------------

        if usuario_id:

            try:

                uuid.UUID(
                    str(usuario_id)
                )

            except (
                ValueError,
                TypeError,
                AttributeError
            ):

                return Response(
                    {
                        "success": False,
                        "message": (
                            "usuario no es un "
                            "identificador válido."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ----------------------------------------------------
        # VALIDAR ESTADO DE VENTA
        # ----------------------------------------------------

        if estado:

            estados_validos = {
                valor
                for valor, _ in Venta.ESTADOS
            }

            if estado not in estados_validos:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "El estado de venta "
                            "no es válido."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = reporte_ventas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            usuario_id=usuario_id,
            estado=estado
        )

        paginator, pagina = _paginar(
            request,
            data
        )

        serializer = ReporteVentaSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )


# ============================================================
# PRODUCTOS MÁS VENDIDOS
# ============================================================

class ReporteProductosView(
    APIView
):

    permission_classes = PERMISSION_ADMIN

    def get(
        self,
        request
    ):

        fecha_inicio, error = _parsear_fecha(
            request.query_params.get(
                "fecha_inicio"
            ),
            "fecha_inicio"
        )

        if error:
            return error

        fecha_fin, error = _parsear_fecha(
            request.query_params.get(
                "fecha_fin"
            ),
            "fecha_fin"
        )

        if error:
            return error

        error_rango = _validar_rango(
            fecha_inicio,
            fecha_fin
        )

        if error_rango:
            return error_rango

        data = reporte_productos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        paginator, pagina = _paginar(
            request,
            data
        )

        serializer = ReporteProductoSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )


# ============================================================
# INVENTARIO
# ============================================================

class ReporteInventarioView(
    APIView
):

    permission_classes = PERMISSION_EMPLEADO

    def get(
        self,
        request
    ):

        data = reporte_inventario()

        paginator, pagina = _paginar(
            request,
            data
        )

        serializer = ReporteInventarioSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )


# ============================================================
# STOCK BAJO
# ============================================================

class ReporteStockBajoView(
    APIView
):

    permission_classes = PERMISSION_EMPLEADO

    def get(
        self,
        request
    ):

        data = reporte_stock_bajo()

        paginator, pagina = _paginar(
            request,
            data
        )

        serializer = ReporteStockBajoSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )


# ============================================================
# CORTES DE CAJA
# ============================================================

class ReporteCortesView(
    APIView
):

    permission_classes = PERMISSION_ADMIN

    def get(
        self,
        request
    ):

        fecha_inicio, error = _parsear_fecha(
            request.query_params.get(
                "fecha_inicio"
            ),
            "fecha_inicio"
        )

        if error:
            return error

        fecha_fin, error = _parsear_fecha(
            request.query_params.get(
                "fecha_fin"
            ),
            "fecha_fin"
        )

        if error:
            return error

        error_rango = _validar_rango(
            fecha_inicio,
            fecha_fin
        )

        if error_rango:
            return error_rango

        data = reporte_cortes(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        paginator, pagina = _paginar(
            request,
            data
        )

        serializer = ReporteCorteSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )


# ============================================================
# DEVOLUCIONES
# ============================================================

class ReporteDevolucionesView(
    APIView
):

    permission_classes = PERMISSION_ADMIN

    def get(
        self,
        request
    ):

        fecha_inicio, error = _parsear_fecha(
            request.query_params.get(
                "fecha_inicio"
            ),
            "fecha_inicio"
        )

        if error:
            return error

        fecha_fin, error = _parsear_fecha(
            request.query_params.get(
                "fecha_fin"
            ),
            "fecha_fin"
        )

        if error:
            return error

        error_rango = _validar_rango(
            fecha_inicio,
            fecha_fin
        )

        if error_rango:
            return error_rango

        data = reporte_devoluciones(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        paginator, pagina = _paginar(
            request,
            data
        )

        serializer = ReporteDevolucionSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )


# ============================================================
# GARANTÍAS
# ============================================================

class ReporteGarantiasView(
    APIView
):

    permission_classes = PERMISSION_ADMIN

    def get(
        self,
        request
    ):

        fecha_inicio, error = _parsear_fecha(
            request.query_params.get(
                "fecha_inicio"
            ),
            "fecha_inicio"
        )

        if error:
            return error

        fecha_fin, error = _parsear_fecha(
            request.query_params.get(
                "fecha_fin"
            ),
            "fecha_fin"
        )

        if error:
            return error

        error_rango = _validar_rango(
            fecha_inicio,
            fecha_fin
        )

        if error_rango:
            return error_rango

        estado = request.query_params.get(
            "estado"
        )

        # ----------------------------------------------------
        # VALIDAR ESTADO DE GARANTÍA
        # ----------------------------------------------------

        if estado:

            campo_estado = Garantia._meta.get_field(
                "estado"
            )

            estados_validos = {
                valor
                for valor, _ in campo_estado.choices
            }

            if estado not in estados_validos:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "El estado de garantía "
                            "no es válido."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = reporte_garantias(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=estado
        )

        paginator, pagina = _paginar(
            request,
            data
        )

        serializer = ReporteGarantiaSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )


# ============================================================
# MOVIMIENTOS DE INVENTARIO
# ============================================================

class ReporteMovimientosView(
    APIView
):

    permission_classes = PERMISSION_ADMIN

    def get(
        self,
        request
    ):

        fecha_inicio, error = _parsear_fecha(
            request.query_params.get(
                "fecha_inicio"
            ),
            "fecha_inicio"
        )

        if error:
            return error

        fecha_fin, error = _parsear_fecha(
            request.query_params.get(
                "fecha_fin"
            ),
            "fecha_fin"
        )

        if error:
            return error

        error_rango = _validar_rango(
            fecha_inicio,
            fecha_fin
        )

        if error_rango:
            return error_rango

        tipo = request.query_params.get(
            "tipo"
        )

        # ----------------------------------------------------
        # VALIDAR TIPO DE MOVIMIENTO
        # ----------------------------------------------------

        if tipo:

            tipos_validos = {
                valor
                for valor, _ in MovimientoInventario.TIPOS
            }

            if tipo not in tipos_validos:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "El tipo de movimiento "
                            "no es válido."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = reporte_movimientos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo=tipo
        )

        paginator, pagina = _paginar(
            request,
            data
        )

        serializer = ReporteMovimientoSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )