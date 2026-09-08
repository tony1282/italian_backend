from decimal import Decimal

from django.db.models import Sum, F, Count, Prefetch
from django.utils import timezone

from ventas.models import Venta
from detalle_venta.models import DetalleVenta
from variantes.models import Variante
from inventario.models import MovimientoInventario
from corte_caja.models import CorteCaja, MovimientoCaja
from devoluciones.models import Devolucion, DetalleDevolucion
from garantias.models import Garantia


# ============================================================
# UTILIDADES
# ============================================================

def dinero(valor):
    return (
        valor or Decimal("0.00")
    ).quantize(
        Decimal("0.01")
    )


def _nombre_usuario(obj):
    return f"{obj.nombre} {obj.apellido}"


def _totales_por_metodo(qs, campo_monto):
    """
    Dado un queryset con metodo_pago__nombre,
    devuelve:

        {
            nombre_metodo: total
        }

    utilizando values + annotate.
    """

    rows = (
        qs
        .values("metodo_pago__nombre")
        .annotate(
            total=Sum(campo_monto)
        )
    )

    return {
        row["metodo_pago__nombre"]:
            dinero(row["total"])
        for row in rows
    }


def _aplicar_filtros_fecha(
    qs,
    campo,
    fecha_inicio,
    fecha_fin,
):
    """
    Aplica filtros inclusivos por fecha.
    """

    if fecha_inicio:

        qs = qs.filter(
            **{
                f"{campo}__date__gte":
                    fecha_inicio
            }
        )

    if fecha_fin:

        qs = qs.filter(
            **{
                f"{campo}__date__lte":
                    fecha_fin
            }
        )

    return qs


# ============================================================
# HELPERS DE CÁLCULO
# REPORTE PRODUCTOS
# ============================================================

def _cantidades_devueltas(venta):

    resultado = {}

    for devolucion in venta.devoluciones.all():

        for detalle_devolucion in (
            devolucion.detalles.all()
        ):

            resultado[
                detalle_devolucion.detalle_venta_id
            ] = (
                resultado.get(
                    detalle_devolucion.detalle_venta_id,
                    0,
                )
                + detalle_devolucion.cantidad
            )

    return resultado


def _calcular_total_detalle(
    detalle,
    cantidad_vendida,
    descuento_venta,
    subtotal_original_venta,
    subtotal_neto_venta,
    iva_venta,
):

    cantidad_original = int(
        detalle.cantidad
    )

    subtotal_detalle = (
        detalle.subtotal
        or Decimal("0.00")
    )

    proporcion = (
        subtotal_detalle
        / subtotal_original_venta
    )

    base_neta = max(
        subtotal_detalle
        - descuento_venta * proporcion,
        Decimal("0.00"),
    )

    if subtotal_neto_venta > Decimal("0.00"):

        iva_detalle = (
            iva_venta
            * (
                base_neta
                / subtotal_neto_venta
            )
        )

    else:

        iva_detalle = Decimal("0.00")

    total = (
        base_neta
        + iva_detalle
    ) * (
        Decimal(cantidad_vendida)
        / Decimal(cantidad_original)
    )

    return total


# ============================================================
# REPORTE RESUMEN DEL DÍA
# ============================================================

def _metodos_dict(
    totales_por_metodo
):

    return {

        "efectivo":
            totales_por_metodo.get(
                "EFECTIVO",
                dinero(None),
            ),

        "tarjeta":
            totales_por_metodo.get(
                "TARJETA",
                dinero(None),
            ),

        "transferencia":
            totales_por_metodo.get(
                "TRANSFERENCIA",
                dinero(None),
            ),
    }


def reporte_resumen_dia(
    fecha=None
):

    if fecha is None:
        fecha = timezone.localdate()

    # --------------------------------------------------------
    # Ventas completadas o devueltas: una venta devuelta sí
    # generó ingreso ese día (el reembolso se resta aparte,
    # más abajo, contra su propia fecha). Mismo criterio ya
    # aplicado en corte_caja para evitar que el dinero de una
    # venta desaparezca del reporte del día en que se vendió.
    # --------------------------------------------------------

    ventas = Venta.objects.filter(
        fecha__date=fecha,
        estado__in=["COMPLETADA", "DEVUELTA"],
    )

    resumen = ventas.aggregate(

        cantidad_ventas=Count(
            "id"
        ),

        subtotal=Sum(
            "subtotal"
        ),

        descuento=Sum(
            "descuento"
        ),

        iva=Sum(
            "iva"
        ),

        total=Sum(
            "total"
        ),
    )

    total_vendido = dinero(
        resumen["total"]
    )

    # --------------------------------------------------------
    # Reembolsos
    # --------------------------------------------------------

    reembolsos_qs = (
        MovimientoCaja.objects.filter(
            fecha__date=fecha,
            tipo="REEMBOLSO",
        )
    )

    reembolsos = dinero(
        reembolsos_qs.aggregate(
            total=Sum("monto")
        )["total"]
    )

    return {

        "fecha":
            fecha,

        "cantidad_ventas":
            resumen["cantidad_ventas"]
            or 0,

        "subtotal":
            dinero(
                resumen["subtotal"]
            ),

        "descuento":
            dinero(
                resumen["descuento"]
            ),

        "iva":
            dinero(
                resumen["iva"]
            ),

        "total_vendido":
            total_vendido,

        "reembolsos":
            reembolsos,

        "venta_neta":
            dinero(
                total_vendido
                - reembolsos
            ),

        "metodos_pago":
            _metodos_dict(
                _totales_por_metodo(
                    ventas,
                    "total",
                )
            ),

        "reembolsos_por_metodo":
            _metodos_dict(
                _totales_por_metodo(
                    reembolsos_qs,
                    "monto",
                )
            ),
    }


# ============================================================
# REPORTE DE VENTAS
# ============================================================

def reporte_ventas(
    fecha_inicio=None,
    fecha_fin=None,
    usuario_id=None,
    estado=None,
):

    qs = (
        Venta.objects
        .select_related(
            "usuario",
            "metodo_pago",
        )
        .order_by("-fecha")
    )

    qs = _aplicar_filtros_fecha(
        qs,
        "fecha",
        fecha_inicio,
        fecha_fin,
    )

    if usuario_id:

        qs = qs.filter(
            usuario_id=usuario_id
        )

    if estado:

        qs = qs.filter(
            estado=estado
        )

    return [

        {

            "id":
                venta.id,

            "folio":
                venta.folio,

            "fecha":
                venta.fecha,

            "usuario":
                _nombre_usuario(
                    venta.usuario
                ),

            "metodo_pago":
                venta.metodo_pago.nombre,

            "subtotal":
                dinero(
                    venta.subtotal
                ),

            "descuento":
                dinero(
                    venta.descuento
                ),

            "iva":
                dinero(
                    venta.iva
                ),

            "total":
                dinero(
                    venta.total
                ),

            "estado":
                venta.estado,
        }

        for venta in qs
    ]


# ============================================================
# PRODUCTOS MÁS VENDIDOS
# ============================================================

def _acumular_detalle(
    detalle,
    cantidades_devueltas,
    descuento_venta,
    subtotal_original,
    subtotal_neto,
    iva_venta,
    productos,
):

    cantidad_original = int(
        detalle.cantidad
    )

    if cantidad_original <= 0:
        return

    cantidad_vendida = (
        cantidad_original
        - int(
            cantidades_devueltas.get(
                detalle.id,
                0,
            )
        )
    )

    if cantidad_vendida <= 0:
        return

    total_detalle = (
        _calcular_total_detalle(
            detalle,
            cantidad_vendida,
            descuento_venta,
            subtotal_original,
            subtotal_neto,
            iva_venta,
        )
    )

    variante_id = (
        detalle.variante_id
    )

    if variante_id not in productos:

        productos[variante_id] = {

            "producto":
                detalle.variante
                .producto
                .nombre,

            "variante":
                detalle.variante
                .nombre,

            "cantidad_vendida":
                0,

            "total_generado":
                Decimal("0.00"),
        }

    productos[
        variante_id
    ][
        "cantidad_vendida"
    ] += cantidad_vendida

    productos[
        variante_id
    ][
        "total_generado"
    ] += total_detalle


def _procesar_venta_productos(
    venta,
    productos,
):

    detalles = list(
        venta.detalles.all()
    )

    if not detalles:
        return

    subtotal_original = sum(
        detalle.subtotal
        or Decimal("0.00")
        for detalle in detalles
    )

    if (
        subtotal_original
        <= Decimal("0.00")
    ):
        return

    descuento_venta = (
        venta.descuento
        or Decimal("0.00")
    )

    subtotal_neto = (
        venta.subtotal
        or Decimal("0.00")
    )

    iva_venta = (
        venta.iva
        or Decimal("0.00")
    )

    cantidades_devueltas = (
        _cantidades_devueltas(
            venta
        )
    )

    for detalle in detalles:

        _acumular_detalle(
            detalle,
            cantidades_devueltas,
            descuento_venta,
            subtotal_original,
            subtotal_neto,
            iva_venta,
            productos,
        )


def reporte_productos(
    fecha_inicio=None,
    fecha_fin=None,
):

    ventas = (
        Venta.objects
        .filter(
            estado="COMPLETADA"
        )
        .prefetch_related(

            Prefetch(
                "detalles",
                queryset=(
                    DetalleVenta.objects
                    .select_related(
                        "variante",
                        "variante__producto",
                    )
                ),
            ),

            Prefetch(
                "devoluciones",
                queryset=(
                    Devolucion.objects
                    .filter(
                        estado="APROBADA"
                    )
                    .prefetch_related(
                        "detalles"
                    )
                ),
            ),
        )
    )

    ventas = _aplicar_filtros_fecha(
        ventas,
        "fecha",
        fecha_inicio,
        fecha_fin,
    )

    productos = {}

    for venta in ventas:

        _procesar_venta_productos(
            venta,
            productos,
        )

    for item in productos.values():

        item["total_generado"] = dinero(
            item["total_generado"]
        )

    return sorted(
        productos.values(),
        key=lambda item: (
            item["cantidad_vendida"],
            item["total_generado"],
        ),
        reverse=True,
    )


# ============================================================
# INVENTARIO ACTUAL
# ============================================================

def reporte_inventario():

    variantes = (
        Variante.objects
        .select_related(
            "producto"
        )
        .filter(
            activo=True
        )
        .order_by(
            "producto__nombre",
            "nombre",
        )
    )

    return [

        {

            "id":
                variante.id,

            "producto":
                variante.producto.nombre,

            "variante":
                variante.nombre,

            "sku":
                variante.sku,

            "codigo_barras":
                variante.codigo_barras,

            "stock_actual":
                variante.stock,

            "stock_defectuoso":
                variante.stock_defectuoso,

            "stock_minimo":
                variante.stock_minimo,

            "costo":
                dinero(
                    variante.costo
                ),

            "precio_menudeo":
                dinero(
                    variante.precio_menudeo
                ),

            "precio_mayoreo":
                dinero(
                    variante.precio_mayoreo
                ),

            "activo":
                variante.activo,
        }

        for variante in variantes
    ]


# ============================================================
# STOCK BAJO
# ============================================================

def reporte_stock_bajo():

    variantes = (
        Variante.objects
        .select_related(
            "producto"
        )
        .filter(
            activo=True,
            stock__lte=F(
                "stock_minimo"
            ),
        )
        .order_by(
            "stock"
        )
    )

    return [

        {

            "id":
                variante.id,

            "producto":
                variante.producto.nombre,

            "variante":
                variante.nombre,

            "stock_actual":
                variante.stock,

            "stock_defectuoso":
                variante.stock_defectuoso,

            "stock_minimo":
                variante.stock_minimo,

            "necesita_reposicion":
                True,
        }

        for variante in variantes
    ]


# ============================================================
# CORTES DE CAJA
# ============================================================

def reporte_cortes(
    fecha_inicio=None,
    fecha_fin=None,
):

    qs = (
        CorteCaja.objects
        .select_related(
            "caja",
            "usuario",
        )
        .order_by(
            "-fecha_inicio"
        )
    )

    qs = _aplicar_filtros_fecha(
        qs,
        "fecha_inicio",
        fecha_inicio,
        fecha_fin,
    )

    return [

        {

            "id":
                corte.id,

            "caja":
                str(corte.caja),

            "usuario":
                _nombre_usuario(
                    corte.usuario
                ),

            "fecha_inicio":
                corte.fecha_inicio,

            "fecha_fin":
                corte.fecha_fin,

            "efectivo_inicial":
                dinero(
                    corte.efectivo_inicial
                ),

            "efectivo_final":
                (
                    dinero(
                        corte.efectivo_final
                    )
                    if corte.efectivo_final
                    is not None
                    else None
                ),

            "diferencia":
                (
                    dinero(
                        corte.diferencia
                    )
                    if corte.diferencia
                    is not None
                    else None
                ),
        }

        for corte in qs
    ]


# ============================================================
# DEVOLUCIONES
# ============================================================

def _serializar_devolucion(
    devolucion
):

    return {

        "id":
            devolucion.id,

        "venta_folio":
            devolucion.venta.folio,

        "usuario":
            _nombre_usuario(
                devolucion.usuario
            ),

        "tipo":
            devolucion.tipo,

        "motivo":
            devolucion.motivo,

        "estado":
            devolucion.estado,

        "total_devuelto":
            dinero(
                devolucion.total_devuelto
            ),

        "fecha":
            devolucion.fecha,

        "productos": [

            {

                "producto":
                    detalle
                    .detalle_venta
                    .variante
                    .producto
                    .nombre,

                "variante":
                    detalle
                    .detalle_venta
                    .variante
                    .nombre,

                "cantidad":
                    detalle.cantidad,

                "subtotal":
                    dinero(
                        detalle.subtotal
                    ),
            }

            for detalle
            in devolucion.detalles.all()
        ],
    }


def reporte_devoluciones(
    fecha_inicio=None,
    fecha_fin=None,
    estado=None,
):

    qs = (
        Devolucion.objects
        .select_related(
            "venta",
            "usuario",
        )
        .prefetch_related(
            "detalles__detalle_venta__variante__producto"
        )
        .order_by(
            "-fecha"
        )
    )

    qs = _aplicar_filtros_fecha(
        qs,
        "fecha",
        fecha_inicio,
        fecha_fin,
    )

    # --------------------------------------------------------
    # FILTRO POR ESTADO
    # --------------------------------------------------------

    if estado:

        qs = qs.filter(
            estado=estado
        )

    return [
        _serializar_devolucion(
            devolucion
        )
        for devolucion in qs
    ]


# ============================================================
# GARANTÍAS
# ============================================================

def _serializar_garantia(
    garantia
):

    return {

        "id":
            garantia.id,

        "venta_folio":
            garantia.venta.folio,

        "producto":
            garantia.variante
            .producto
            .nombre,

        "variante":
            garantia.variante
            .nombre,

        "variante_nueva":
            (
                garantia.variante_nueva.nombre
                if garantia.variante_nueva
                else None
            ),

        "cantidad":
            garantia.cantidad,

        "usuario":
            _nombre_usuario(
                garantia.usuario
            ),

        "motivo":
            garantia.motivo,

        "estado":
            garantia.estado,

        "resolucion":
            garantia.resolucion,

        "observaciones":
            garantia.observaciones,

        "fecha":
            garantia.fecha,

        "fecha_actualizacion":
            garantia.fecha_actualizacion,
    }


def reporte_garantias(
    fecha_inicio=None,
    fecha_fin=None,
    estado=None,
):

    qs = (
        Garantia.objects
        .select_related(
            "venta",
            "variante",
            "variante__producto",
            "variante_nueva",
            "usuario",
        )
        .order_by(
            "-fecha"
        )
    )

    qs = _aplicar_filtros_fecha(
        qs,
        "fecha",
        fecha_inicio,
        fecha_fin,
    )

    if estado:

        qs = qs.filter(
            estado=estado
        )

    return [
        _serializar_garantia(
            garantia
        )
        for garantia in qs
    ]


# ============================================================
# MOVIMIENTOS DE INVENTARIO
# ============================================================

def _serializar_movimiento(
    movimiento
):

    return {

        "id":
            movimiento.id,

        "producto":
            movimiento
            .variante
            .producto
            .nombre,

        "variante":
            movimiento
            .variante
            .nombre,

        "tipo":
            movimiento.tipo,

        "stock_anterior":
            movimiento.stock_anterior,

        "cantidad":
            movimiento.cantidad,

        "stock_nuevo":
            movimiento.stock_nuevo,

        "stock_defectuoso_anterior":
            movimiento
            .stock_defectuoso_anterior,

        "stock_defectuoso_nuevo":
            movimiento
            .stock_defectuoso_nuevo,

        "observaciones":
            movimiento.observaciones,

        "usuario":
            _nombre_usuario(
                movimiento.usuario
            ),

        "fecha":
            movimiento.fecha,
    }


def reporte_movimientos(
    fecha_inicio=None,
    fecha_fin=None,
    tipo=None,
):

    qs = (
        MovimientoInventario.objects
        .select_related(
            "variante",
            "variante__producto",
            "usuario",
        )
        .order_by(
            "-fecha"
        )
    )

    qs = _aplicar_filtros_fecha(
        qs,
        "fecha",
        fecha_inicio,
        fecha_fin,
    )

    if tipo:

        qs = qs.filter(
            tipo=tipo
        )

    return [
        _serializar_movimiento(
            movimiento
        )
        for movimiento in qs
    ]