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
    return (valor or Decimal("0.00")).quantize(Decimal("0.01"))


def _nombre_usuario(obj):
    return f"{obj.nombre} {obj.apellido}"


def _totales_por_metodo(qs, campo_monto):
    """
    Dado un queryset con metodo_pago__nombre, devuelve un dict
    {nombre_metodo: total} en una sola query usando values+annotate.
    """
    rows = (
        qs
        .values("metodo_pago__nombre")
        .annotate(total=Sum(campo_monto))
    )
    return {r["metodo_pago__nombre"]: dinero(r["total"]) for r in rows}


def _aplicar_filtros_fecha(qs, campo, fecha_inicio, fecha_fin):
    if fecha_inicio:
        qs = qs.filter(**{f"{campo}__date__gte": fecha_inicio})
    if fecha_fin:
        qs = qs.filter(**{f"{campo}__date__lte": fecha_fin})
    return qs


# ============================================================
# HELPERS DE CÁLCULO (reporte_productos)
# ============================================================

def _cantidades_devueltas(venta):
    resultado = {}
    for devolucion in venta.devoluciones.all():
        for dd in devolucion.detalles.all():
            resultado[dd.detalle_venta_id] = resultado.get(dd.detalle_venta_id, 0) + dd.cantidad
    return resultado


def _calcular_total_detalle(detalle, cantidad_vendida, descuento_venta,
                             subtotal_original_venta, subtotal_neto_venta, iva_venta):
    cantidad_original = int(detalle.cantidad)
    subtotal_detalle = detalle.subtotal or Decimal("0.00")

    proporcion = subtotal_detalle / subtotal_original_venta
    base_neta = max(subtotal_detalle - descuento_venta * proporcion, Decimal("0.00"))

    if subtotal_neto_venta > Decimal("0.00"):
        iva_detalle = iva_venta * (base_neta / subtotal_neto_venta)
    else:
        iva_detalle = Decimal("0.00")

    total = (base_neta + iva_detalle) * (Decimal(cantidad_vendida) / Decimal(cantidad_original))
    return total


# ============================================================
# REPORTE RESUMEN DEL DÍA
# ============================================================

def _metodos_dict(totales_por_metodo):
    return {
        "efectivo": totales_por_metodo.get("EFECTIVO", dinero(None)),
        "tarjeta": totales_por_metodo.get("TARJETA", dinero(None)),
        "transferencia": totales_por_metodo.get("TRANSFERENCIA", dinero(None)),
    }


def reporte_resumen_dia(fecha=None):
    if fecha is None:
        fecha = timezone.localdate()

    ventas = Venta.objects.filter(fecha__date=fecha, estado="COMPLETADA")
    resumen = ventas.aggregate(
        cantidad_ventas=Count("id"),
        subtotal=Sum("subtotal"),
        descuento=Sum("descuento"),
        iva=Sum("iva"),
        total=Sum("total"),
    )
    total_vendido = dinero(resumen["total"])

    reembolsos_qs = MovimientoCaja.objects.filter(fecha__date=fecha, tipo="REEMBOLSO")
    reembolsos = dinero(reembolsos_qs.aggregate(total=Sum("monto"))["total"])

    return {
        "fecha": fecha,
        "cantidad_ventas": resumen["cantidad_ventas"] or 0,
        "subtotal": dinero(resumen["subtotal"]),
        "descuento": dinero(resumen["descuento"]),
        "iva": dinero(resumen["iva"]),
        "total_vendido": total_vendido,
        "reembolsos": reembolsos,
        "venta_neta": dinero(total_vendido - reembolsos),
        "metodos_pago": _metodos_dict(_totales_por_metodo(ventas, "total")),
        "reembolsos_por_metodo": _metodos_dict(_totales_por_metodo(reembolsos_qs, "monto")),
    }


# ============================================================
# REPORTE DE VENTAS
# ============================================================

def reporte_ventas(fecha_inicio=None, fecha_fin=None, usuario_id=None, estado=None):
    qs = Venta.objects.select_related("usuario", "metodo_pago").order_by("-fecha")
    qs = _aplicar_filtros_fecha(qs, "fecha", fecha_inicio, fecha_fin)

    if usuario_id:
        qs = qs.filter(usuario_id=usuario_id)
    if estado:
        qs = qs.filter(estado=estado)

    return [
        {
            "id": v.id,
            "folio": v.folio,
            "fecha": v.fecha,
            "usuario": _nombre_usuario(v.usuario),
            "metodo_pago": v.metodo_pago.nombre,
            "subtotal": dinero(v.subtotal),
            "descuento": dinero(v.descuento),
            "iva": dinero(v.iva),
            "total": dinero(v.total),
            "estado": v.estado,
        }
        for v in qs
    ]


# ============================================================
# PRODUCTOS MÁS VENDIDOS
# ============================================================

def _acumular_detalle(
    detalle, cantidades_devueltas, descuento_venta,
    subtotal_original, subtotal_neto, iva_venta, productos,
):
    cantidad_original = int(detalle.cantidad)
    if cantidad_original <= 0:
        return

    cantidad_vendida = cantidad_original - int(cantidades_devueltas.get(detalle.id, 0))
    if cantidad_vendida <= 0:
        return

    total_detalle = _calcular_total_detalle(
        detalle, cantidad_vendida, descuento_venta,
        subtotal_original, subtotal_neto, iva_venta,
    )

    vid = detalle.variante_id
    if vid not in productos:
        productos[vid] = {
            "producto": detalle.variante.producto.nombre,
            "variante": detalle.variante.nombre,
            "cantidad_vendida": 0,
            "total_generado": Decimal("0.00"),
        }

    productos[vid]["cantidad_vendida"] += cantidad_vendida
    productos[vid]["total_generado"] += total_detalle


def _procesar_venta_productos(venta, productos):
    detalles = list(venta.detalles.all())
    if not detalles:
        return

    subtotal_original = sum(d.subtotal or Decimal("0.00") for d in detalles)
    if subtotal_original <= Decimal("0.00"):
        return

    descuento_venta = venta.descuento or Decimal("0.00")
    subtotal_neto = venta.subtotal or Decimal("0.00")
    iva_venta = venta.iva or Decimal("0.00")
    cantidades_devueltas = _cantidades_devueltas(venta)

    for detalle in detalles:
        _acumular_detalle(
            detalle, cantidades_devueltas, descuento_venta,
            subtotal_original, subtotal_neto, iva_venta, productos,
        )


def reporte_productos(fecha_inicio=None, fecha_fin=None):
    ventas = (
        Venta.objects
        .filter(estado="COMPLETADA")
        .prefetch_related(
            Prefetch(
                "detalles",
                queryset=DetalleVenta.objects.select_related("variante", "variante__producto"),
            ),
            Prefetch(
                "devoluciones",
                queryset=Devolucion.objects.filter(estado="APROBADA").prefetch_related("detalles"),
            ),
        )
    )
    ventas = _aplicar_filtros_fecha(ventas, "fecha", fecha_inicio, fecha_fin)

    productos = {}
    for venta in ventas:
        _procesar_venta_productos(venta, productos)

    for item in productos.values():
        item["total_generado"] = dinero(item["total_generado"])

    return sorted(
        productos.values(),
        key=lambda x: (x["cantidad_vendida"], x["total_generado"]),
        reverse=True,
    )


# ============================================================
# INVENTARIO ACTUAL
# ============================================================

def reporte_inventario():
    variantes = (
        Variante.objects
        .select_related("producto")
        .filter(activo=True)
        .order_by("producto__nombre", "nombre")
    )

    return [
        {
            "id": v.id,
            "producto": v.producto.nombre,
            "variante": v.nombre,
            "sku": v.sku,
            "codigo_barras": v.codigo_barras,
            "stock_actual": v.stock,
            "stock_defectuoso": v.stock_defectuoso,
            "stock_minimo": v.stock_minimo,
            "costo": dinero(v.costo),
            "precio_menudeo": dinero(v.precio_menudeo),
            "precio_mayoreo": dinero(v.precio_mayoreo),
            "activo": v.activo,
        }
        for v in variantes
    ]


# ============================================================
# STOCK BAJO
# ============================================================

def reporte_stock_bajo():
    variantes = (
        Variante.objects
        .select_related("producto")
        .filter(activo=True, stock__lte=F("stock_minimo"))
        .order_by("stock")
    )

    return [
        {
            "id": v.id,
            "producto": v.producto.nombre,
            "variante": v.nombre,
            "stock_actual": v.stock,
            "stock_defectuoso": v.stock_defectuoso,
            "stock_minimo": v.stock_minimo,
            "necesita_reposicion": True,
        }
        for v in variantes
    ]


# ============================================================
# CORTES DE CAJA
# ============================================================

def reporte_cortes(fecha_inicio=None, fecha_fin=None):
    qs = CorteCaja.objects.select_related("caja", "usuario").order_by("-fecha_inicio")
    qs = _aplicar_filtros_fecha(qs, "fecha_inicio", fecha_inicio, fecha_fin)

    return [
        {
            "id": c.id,
            "caja": str(c.caja),
            "usuario": _nombre_usuario(c.usuario),
            "fecha_inicio": c.fecha_inicio,
            "fecha_fin": c.fecha_fin,
            "efectivo_inicial": dinero(c.efectivo_inicial),
            "efectivo_final": dinero(c.efectivo_final) if c.efectivo_final is not None else None,
            "diferencia": dinero(c.diferencia) if c.diferencia is not None else None,
        }
        for c in qs
    ]


# ============================================================
# DEVOLUCIONES
# ============================================================

def _serializar_devolucion(d):
    return {
        "id": d.id,
        "venta_folio": d.venta.folio,
        "usuario": _nombre_usuario(d.usuario),
        "tipo": d.tipo,
        "motivo": d.motivo,
        "estado": d.estado,
        "total_devuelto": dinero(d.total_devuelto),
        "fecha": d.fecha,
        "productos": [
            {
                "producto": det.detalle_venta.variante.producto.nombre,
                "variante": det.detalle_venta.variante.nombre,
                "cantidad": det.cantidad,
                "subtotal": dinero(det.subtotal),
            }
            for det in d.detalles.all()
        ],
    }


def reporte_devoluciones(fecha_inicio=None, fecha_fin=None):
    qs = (
        Devolucion.objects
        .select_related("venta", "usuario")
        .prefetch_related("detalles__detalle_venta__variante__producto")
        .order_by("-fecha")
    )
    qs = _aplicar_filtros_fecha(qs, "fecha", fecha_inicio, fecha_fin)
    return [_serializar_devolucion(d) for d in qs]


# ============================================================
# GARANTÍAS
# ============================================================

def _serializar_garantia(g):
    return {
        "id": g.id,
        "venta_folio": g.venta.folio,
        "producto": g.variante.producto.nombre,
        "variante": g.variante.nombre,
        "variante_nueva": g.variante_nueva.nombre if g.variante_nueva else None,
        "cantidad": g.cantidad,
        "usuario": _nombre_usuario(g.usuario),
        "motivo": g.motivo,
        "estado": g.estado,
        "resolucion": g.resolucion,
        "observaciones": g.observaciones,
        "fecha": g.fecha,
        "fecha_actualizacion": g.fecha_actualizacion,
    }


def reporte_garantias(fecha_inicio=None, fecha_fin=None, estado=None):
    qs = (
        Garantia.objects
        .select_related("venta", "variante", "variante__producto", "variante_nueva", "usuario")
        .order_by("-fecha")
    )
    qs = _aplicar_filtros_fecha(qs, "fecha", fecha_inicio, fecha_fin)
    if estado:
        qs = qs.filter(estado=estado)
    return [_serializar_garantia(g) for g in qs]


# ============================================================
# MOVIMIENTOS DE INVENTARIO
# ============================================================

def _serializar_movimiento(m):
    return {
        "id": m.id,
        "producto": m.variante.producto.nombre,
        "variante": m.variante.nombre,
        "tipo": m.tipo,
        "stock_anterior": m.stock_anterior,
        "cantidad": m.cantidad,
        "stock_nuevo": m.stock_nuevo,
        "stock_defectuoso_anterior": m.stock_defectuoso_anterior,
        "stock_defectuoso_nuevo": m.stock_defectuoso_nuevo,
        "observaciones": m.observaciones,
        "usuario": _nombre_usuario(m.usuario),
        "fecha": m.fecha,
    }


def reporte_movimientos(fecha_inicio=None, fecha_fin=None, tipo=None):
    qs = (
        MovimientoInventario.objects
        .select_related("variante", "variante__producto", "usuario")
        .order_by("-fecha")
    )
    qs = _aplicar_filtros_fecha(qs, "fecha", fecha_inicio, fecha_fin)
    if tipo:
        qs = qs.filter(tipo=tipo)
    return [_serializar_movimiento(m) for m in qs]
