from django.db.models import (
    Sum,
    F,
    Count,
    DecimalField,
    ExpressionWrapper
)

from ventas.models import Venta
from variantes.models import Variante
from inventario.models import MovimientoInventario
from corte_caja.models import CorteCaja
from devoluciones.models import Devolucion
from garantias.models import Garantia


# ============================================================
# REPORTE DE VENTAS
# ============================================================

def reporte_ventas(
    fecha_inicio=None,
    fecha_fin=None,
    usuario_id=None,
    estado=None
):

    ventas = (
        Venta.objects
        .select_related(
            "usuario",
            "metodo_pago"
        )
        .all()
    )

    # --------------------------------------------------------
    # Filtros
    # --------------------------------------------------------

    if fecha_inicio:
        ventas = ventas.filter(
            fecha__date__gte=fecha_inicio
        )

    if fecha_fin:
        ventas = ventas.filter(
            fecha__date__lte=fecha_fin
        )

    if usuario_id:
        ventas = ventas.filter(
            usuario_id=usuario_id
        )

    if estado:
        ventas = ventas.filter(
            estado=estado
        )

    # --------------------------------------------------------
    # Resultado
    # --------------------------------------------------------

    data = []

    for venta in ventas:

        data.append(
            {
                "id": venta.id,
                "folio": venta.folio,
                "fecha": venta.fecha,
                "usuario": (
                    f"{venta.usuario.nombre} "
                    f"{venta.usuario.apellido}"
                ),
                "metodo_pago": venta.metodo_pago.nombre,
                "subtotal": venta.subtotal,
                "descuento": venta.descuento,
                "iva": venta.iva,
                "total": venta.total,
                "estado": venta.estado
            }
        )

    return data


# ============================================================
# PRODUCTOS MÁS VENDIDOS
# ============================================================

def reporte_productos():

    detalles = (
        Venta.objects
        .filter(
            estado="COMPLETADA"
        )
        .values(
            "detalles__variante",
            "detalles__variante__nombre",
            "detalles__variante__producto__nombre"
        )
        .annotate(
            cantidad_vendida=Sum(
                "detalles__cantidad"
            ),
            total_generado=Sum(
                "detalles__subtotal"
            )
        )
        .order_by(
            "-cantidad_vendida"
        )
    )

    data = []

    for detalle in detalles:

        data.append(
            {
                "producto": (
                    detalle[
                        "detalles__variante__producto__nombre"
                    ]
                ),
                "variante": (
                    detalle[
                        "detalles__variante__nombre"
                    ]
                ),
                "cantidad_vendida": (
                    detalle["cantidad_vendida"]
                ),
                "total_generado": (
                    detalle["total_generado"]
                )
            }
        )

    return data


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
            "nombre"
        )
    )

    data = []

    for variante in variantes:

        data.append(
            {
                "id": variante.id,
                "producto": variante.producto.nombre,
                "variante": variante.nombre,
                "sku": variante.sku,
                "codigo_barras": variante.codigo_barras,
                "stock_actual": variante.stock,
                "stock_minimo": variante.stock_minimo,
                "costo": variante.costo,
                "precio_menudeo": variante.precio_menudeo,
                "precio_mayoreo": variante.precio_mayoreo,
                "activo": variante.activo
            }
        )

    return data


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
            stock__lte=F("stock_minimo")
        )
        .order_by(
            "stock"
        )
    )

    data = []

    for variante in variantes:

        data.append(
            {
                "id": variante.id,
                "producto": variante.producto.nombre,
                "variante": variante.nombre,
                "stock_actual": variante.stock,
                "stock_minimo": variante.stock_minimo,
                "necesita_reposicion": True
            }
        )

    return data


# ============================================================
# CORTES DE CAJA
# ============================================================

def reporte_cortes():

    cortes = (
        CorteCaja.objects
        .select_related(
            "caja",
            "usuario"
        )
        .all()
        .order_by(
            "-fecha_inicio"
        )
    )

    data = []

    for corte in cortes:

        data.append(
            {
                "id": corte.id,
                "caja": str(corte.caja),
                "usuario": (
                    f"{corte.usuario.nombre} "
                    f"{corte.usuario.apellido}"
                ),
                "fecha_inicio": corte.fecha_inicio,
                "fecha_fin": corte.fecha_fin,
                "efectivo_inicial": corte.efectivo_inicial,
                "efectivo_final": corte.efectivo_final,
                "diferencia": corte.diferencia
            }
        )

    return data


# ============================================================
# DEVOLUCIONES
# ============================================================

def reporte_devoluciones():

    devoluciones = (
        Devolucion.objects
        .select_related(
            "venta",
            "usuario"
        )
        .prefetch_related(
            "detalles__detalle_venta__variante__producto"
        )
        .all()
        .order_by(
            "-fecha"
        )
    )

    data = []

    for devolucion in devoluciones:

        productos = []

        for detalle in devolucion.detalles.all():

            productos.append(
                {
                    "producto": (
                        detalle
                        .detalle_venta
                        .variante
                        .producto
                        .nombre
                    ),
                    "variante": (
                        detalle
                        .detalle_venta
                        .variante
                        .nombre
                    ),
                    "cantidad": detalle.cantidad,
                    "subtotal": detalle.subtotal
                }
            )

        data.append(
            {
                "id": devolucion.id,
                "venta_folio": (
                    devolucion.venta.folio
                ),
                "usuario": (
                    f"{devolucion.usuario.nombre} "
                    f"{devolucion.usuario.apellido}"
                ),
                "tipo": devolucion.tipo,
                "motivo": devolucion.motivo,
                "estado": devolucion.estado,
                "total_devuelto": (
                    devolucion.total_devuelto
                ),
                "productos": productos,
                "fecha": devolucion.fecha
            }
        )

    return data


# ============================================================
# GARANTÍAS
# ============================================================

def reporte_garantias():

    garantias = (
        Garantia.objects
        .select_related(
            "venta",
            "variante",
            "variante__producto",
            "variante_nueva",
            "usuario"
        )
        .all()
        .order_by(
            "-fecha"
        )
    )

    data = []

    for garantia in garantias:

        data.append(
            {
                "id": garantia.id,
                "venta_folio": (
                    garantia.venta.folio
                ),
                "producto": (
                    garantia.variante
                    .producto
                    .nombre
                ),
                "variante": (
                    garantia.variante.nombre
                ),
                "variante_nueva": (
                    garantia.variante_nueva.nombre
                    if garantia.variante_nueva
                    else None
                ),
                "cantidad": garantia.cantidad,
                "usuario": (
                    f"{garantia.usuario.nombre} "
                    f"{garantia.usuario.apellido}"
                ),
                "motivo": garantia.motivo,
                "estado": garantia.estado,
                "resolucion": garantia.resolucion,
                "observaciones": garantia.observaciones,
                "fecha": garantia.fecha,
                "fecha_actualizacion": (
                    garantia.fecha_actualizacion
                )
            }
        )

    return data


# ============================================================
# MOVIMIENTOS DE INVENTARIO
# ============================================================

def reporte_movimientos():

    movimientos = (
        MovimientoInventario.objects
        .select_related(
            "variante",
            "variante__producto",
            "usuario"
        )
        .all()
        .order_by(
            "-fecha"
        )
    )

    data = []

    for movimiento in movimientos:

        data.append(
            {
                "id": movimiento.id,
                "producto": (
                    movimiento
                    .variante
                    .producto
                    .nombre
                ),
                "variante": (
                    movimiento.variante.nombre
                ),
                "tipo": movimiento.tipo,
                "cantidad": movimiento.cantidad,
                "observaciones": (
                    movimiento.observaciones
                ),
                "usuario": (
                    f"{movimiento.usuario.nombre} "
                    f"{movimiento.usuario.apellido}"
                ),
                "fecha": movimiento.fecha
            }
        )

    return data