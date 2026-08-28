from decimal import Decimal

from django.db.models import (
    Sum,
    F,
    Count,
)
from django.db.models import Prefetch

from django.utils import timezone

from ventas.models import Venta

from variantes.models import Variante

from inventario.models import MovimientoInventario

from corte_caja.models import (
    CorteCaja,
    MovimientoCaja
)

from devoluciones.models import (
    Devolucion,
    DetalleDevolucion
)

from garantias.models import Garantia


# ============================================================
# UTILIDAD
# ============================================================

def dinero(valor):
    """
    Convierte un valor monetario a Decimal con 2 decimales.
    """
    return (
        valor or Decimal("0.00")
    ).quantize(
        Decimal("0.01")
    )


# ============================================================
# REPORTE RESUMEN DEL DÍA
# ============================================================

def reporte_resumen_dia(
    fecha=None
):

    if fecha is None:

        fecha = timezone.localdate()

    # --------------------------------------------------------
    # VENTAS DEL DÍA
    #
    # Solo las ventas que permanecen COMPLETADAS.
    #
    # Una devolución parcial no cambia la venta a DEVUELTA,
    # por lo que sigue contabilizándose.
    #
    # Una devolución total cambia la venta a DEVUELTA y deja
    # de contabilizarse como venta activa.
    # --------------------------------------------------------

    ventas = (
        Venta.objects
        .filter(
            fecha__date=fecha,
            estado="COMPLETADA"
        )
    )

    resumen = ventas.aggregate(
        cantidad_ventas=Count("id"),
        subtotal=Sum("subtotal"),
        descuento=Sum("descuento"),
        iva=Sum("iva"),
        total=Sum("total"),
    )

    cantidad_ventas = (
        resumen["cantidad_ventas"]
        or 0
    )

    subtotal = dinero(
        resumen["subtotal"]
    )

    descuento = dinero(
        resumen["descuento"]
    )

    iva = dinero(
        resumen["iva"]
    )

    # --------------------------------------------------------
    # TOTAL VENDIDO
    #
    # Venta.total YA contiene:
    #
    # subtotal después del descuento + IVA
    # --------------------------------------------------------

    total_vendido = dinero(
        resumen["total"]
    )

    # --------------------------------------------------------
    # VENTAS POR MÉTODO DE PAGO
    # --------------------------------------------------------

    ventas_efectivo = dinero(
        ventas
        .filter(
            metodo_pago__nombre="EFECTIVO"
        )
        .aggregate(
            total=Sum("total")
        )["total"]
    )

    ventas_tarjeta = dinero(
        ventas
        .filter(
            metodo_pago__nombre="TARJETA"
        )
        .aggregate(
            total=Sum("total")
        )["total"]
    )

    ventas_transferencia = dinero(
        ventas
        .filter(
            metodo_pago__nombre="TRANSFERENCIA"
        )
        .aggregate(
            total=Sum("total")
        )["total"]
    )

    # --------------------------------------------------------
    # REEMBOLSOS DEL DÍA
    #
    # Se contabilizan por fecha del movimiento de caja,
    # independientemente de cuándo se realizó la venta.
    # --------------------------------------------------------

    reembolsos_qs = (
        MovimientoCaja.objects
        .filter(
            fecha__date=fecha,
            tipo="REEMBOLSO"
        )
    )

    reembolsos = dinero(
        reembolsos_qs
        .aggregate(
            total=Sum("monto")
        )["total"]
    )

    reembolsos_efectivo = dinero(
        reembolsos_qs
        .filter(
            metodo_pago__nombre="EFECTIVO"
        )
        .aggregate(
            total=Sum("monto")
        )["total"]
    )

    reembolsos_tarjeta = dinero(
        reembolsos_qs
        .filter(
            metodo_pago__nombre="TARJETA"
        )
        .aggregate(
            total=Sum("monto")
        )["total"]
    )

    reembolsos_transferencia = dinero(
        reembolsos_qs
        .filter(
            metodo_pago__nombre="TRANSFERENCIA"
        )
        .aggregate(
            total=Sum("monto")
        )["total"]
    )

    # --------------------------------------------------------
    # VENTA NETA
    #
    # Definición:
    #
    # dinero de ventas COMPLETADAS registradas ese día
    # menos reembolsos registrados ese mismo día.
    # --------------------------------------------------------

    venta_neta = dinero(
        total_vendido
        - reembolsos
    )

    return {

        "fecha": fecha,

        "cantidad_ventas":
            cantidad_ventas,

        "subtotal":
            subtotal,

        "descuento":
            descuento,

        "iva":
            iva,

        "total_vendido":
            total_vendido,

        "reembolsos":
            reembolsos,

        "venta_neta":
            venta_neta,

        "metodos_pago": {

            "efectivo":
                ventas_efectivo,

            "tarjeta":
                ventas_tarjeta,

            "transferencia":
                ventas_transferencia,
        },

        "reembolsos_por_metodo": {

            "efectivo":
                reembolsos_efectivo,

            "tarjeta":
                reembolsos_tarjeta,

            "transferencia":
                reembolsos_transferencia,
        }
    }


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
        .order_by("-fecha")
    )

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

                "metodo_pago": (
                    venta.metodo_pago.nombre
                ),

                "subtotal": dinero(
                    venta.subtotal
                ),

                "descuento": dinero(
                    venta.descuento
                ),

                "iva": dinero(
                    venta.iva
                ),

                "total": dinero(
                    venta.total
                ),

                "estado": venta.estado
            }
        )

    return data


# ============================================================
# PRODUCTOS MÁS VENDIDOS
# ============================================================

def reporte_productos(
    fecha_inicio=None,
    fecha_fin=None
):

    # --------------------------------------------------------
    # SOLO VENTAS QUE SIGUEN ACTIVAS
    #
    # CANCELADA -> excluida
    # DEVUELTA  -> excluida
    # COMPLETADA -> incluida
    #
    # Las devoluciones parciales se descuentan desde
    # DetalleDevolucion.
    # --------------------------------------------------------

    devoluciones_aprobadas = (
        Devolucion.objects
        .filter(
            estado="APROBADA"
        )
        .prefetch_related(
            "detalles"
        )
    )

    detalles_venta_qs = (
        Venta.objects
        .none()
    )

    # --------------------------------------------------------
    # PREFETCH EFICIENTE
    # --------------------------------------------------------

    ventas = (
        Venta.objects
        .filter(
            estado="COMPLETADA"
        )
        .prefetch_related(
            Prefetch(
                "detalles",
                queryset=__import__(
                    "detalle_venta.models",
                    fromlist=["DetalleVenta"]
                ).DetalleVenta.objects.select_related(
                    "variante",
                    "variante__producto"
                )
            ),
            Prefetch(
                "devoluciones",
                queryset=devoluciones_aprobadas
            )
        )
    )

    # --------------------------------------------------------
    # FILTROS DE FECHA
    # --------------------------------------------------------

    if fecha_inicio:

        ventas = ventas.filter(
            fecha__date__gte=fecha_inicio
        )

    if fecha_fin:

        ventas = ventas.filter(
            fecha__date__lte=fecha_fin
        )

    # --------------------------------------------------------
    # ACUMULADOR
    # --------------------------------------------------------

    productos = {}

    # --------------------------------------------------------
    # PROCESAR VENTAS
    # --------------------------------------------------------

    for venta in ventas:

        detalles = list(
            venta.detalles.all()
        )

        if not detalles:
            continue

        # ----------------------------------------------------
        # SUBTOTAL ORIGINAL DE LOS DETALLES
        #
        # IMPORTANTE:
        #
        # Venta.subtotal ya es:
        #
        # subtotal_original - descuento
        #
        # Por eso NO debemos volver a restar Venta.descuento.
        # ----------------------------------------------------

        subtotal_original_venta = sum(
            (
                detalle.subtotal
                or Decimal("0.00")
            )
            for detalle in detalles
        )

        subtotal_original_venta = (
            subtotal_original_venta
            or Decimal("0.00")
        )

        descuento_venta = (
            venta.descuento
            or Decimal("0.00")
        )

        subtotal_neto_venta = (
            venta.subtotal
            or Decimal("0.00")
        )

        iva_venta = (
            venta.iva
            or Decimal("0.00")
        )

        # ----------------------------------------------------
        # SI HAY DATOS INCONSISTENTES, EVITAR DIVISIÓN
        # ----------------------------------------------------

        if subtotal_original_venta <= Decimal("0.00"):

            continue

        # ----------------------------------------------------
        # CANTIDADES DEVUELTAS
        # ----------------------------------------------------

        cantidades_devueltas = {}

        for devolucion in venta.devoluciones.all():

            for detalle_devolucion in (
                devolucion.detalles.all()
            ):

                detalle_id = (
                    detalle_devolucion.detalle_venta_id
                )

                cantidades_devueltas[
                    detalle_id
                ] = (
                    cantidades_devueltas.get(
                        detalle_id,
                        0
                    )
                    + detalle_devolucion.cantidad
                )

        # ----------------------------------------------------
        # PROCESAR CADA DETALLE
        # ----------------------------------------------------

        for detalle in detalles:

            cantidad_original = int(
                detalle.cantidad
            )

            cantidad_devuelta = int(
                cantidades_devueltas.get(
                    detalle.id,
                    0
                )
            )

            # ------------------------------------------------
            # EVITAR DATOS INVÁLIDOS
            # ------------------------------------------------

            if cantidad_original <= 0:
                continue

            # ------------------------------------------------
            # CANTIDAD REAL VENDIDA
            # ------------------------------------------------

            cantidad_vendida = (
                cantidad_original
                - cantidad_devuelta
            )

            if cantidad_vendida <= 0:
                continue

            # ------------------------------------------------
            # SUBTOTAL DEL DETALLE
            # ------------------------------------------------

            subtotal_detalle = (
                detalle.subtotal
                or Decimal("0.00")
            )

            # ------------------------------------------------
            # PARTICIPACIÓN DEL PRODUCTO EN LA VENTA
            #
            # Se utiliza para repartir el descuento global.
            # ------------------------------------------------

            proporcion = (
                subtotal_detalle
                / subtotal_original_venta
            )

            # ------------------------------------------------
            # DESCUENTO PROPORCIONAL
            # ------------------------------------------------

            descuento_detalle = (
                descuento_venta
                * proporcion
            )

            # ------------------------------------------------
            # BASE NETA DEL PRODUCTO
            # ------------------------------------------------

            base_neta_detalle = (
                subtotal_detalle
                - descuento_detalle
            )

            if base_neta_detalle < Decimal("0.00"):

                base_neta_detalle = Decimal(
                    "0.00"
                )

            # ------------------------------------------------
            # IVA PROPORCIONAL
            #
            # El IVA de la venta se distribuye según la
            # participación del importe neto del detalle.
            # ------------------------------------------------

            if subtotal_neto_venta > Decimal("0.00"):

                proporcion_neta = (
                    base_neta_detalle
                    / subtotal_neto_venta
                )

                iva_detalle = (
                    iva_venta
                    * proporcion_neta
                )

            else:

                iva_detalle = Decimal(
                    "0.00"
                )

            # ------------------------------------------------
            # TOTAL DEL DETALLE CON IVA
            # ------------------------------------------------

            total_detalle = (
                base_neta_detalle
                + iva_detalle
            )

            # ------------------------------------------------
            # SI EXISTE DEVOLUCIÓN PARCIAL
            #
            # Solo queda como vendido el porcentaje restante.
            # ------------------------------------------------

            factor_vendido = (
                Decimal(cantidad_vendida)
                / Decimal(cantidad_original)
            )

            total_detalle = (
                total_detalle
                * factor_vendido
            )

            # ------------------------------------------------
            # AGRUPAR POR VARIANTE
            # ------------------------------------------------

            variante_id = (
                detalle.variante_id
            )

            if variante_id not in productos:

                productos[variante_id] = {

                    "producto": (
                        detalle
                        .variante
                        .producto
                        .nombre
                    ),

                    "variante": (
                        detalle
                        .variante
                        .nombre
                    ),

                    "cantidad_vendida": 0,

                    "total_generado":
                        Decimal("0.00")
                }

            # ------------------------------------------------
            # ACUMULAR CANTIDADES
            # ------------------------------------------------

            productos[
                variante_id
            ]["cantidad_vendida"] += (
                cantidad_vendida
            )

            # ------------------------------------------------
            # ACUMULAR TOTAL
            #
            # Redondeamos al final, no en cada operación,
            # para reducir diferencias acumuladas de centavos.
            # ------------------------------------------------

            productos[
                variante_id
            ]["total_generado"] += (
                total_detalle
            )

    # --------------------------------------------------------
    # CONVERTIR A LISTA
    # --------------------------------------------------------

    data = list(
        productos.values()
    )

    # --------------------------------------------------------
    # REDONDEAR DINERO
    # --------------------------------------------------------

    for item in data:

        item["total_generado"] = dinero(
            item["total_generado"]
        )

    # --------------------------------------------------------
    # ORDENAR
    # --------------------------------------------------------

    data.sort(
        key=lambda x: (
            x["cantidad_vendida"],
            x["total_generado"]
        ),
        reverse=True
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

                "stock_minimo":
                    variante.stock_minimo,

                "costo": dinero(
                    variante.costo
                ),

                "precio_menudeo": dinero(
                    variante.precio_menudeo
                ),

                "precio_mayoreo": dinero(
                    variante.precio_mayoreo
                ),

                "activo":
                    variante.activo
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
            stock__lte=F(
                "stock_minimo"
            )
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

                "producto":
                    variante.producto.nombre,

                "variante":
                    variante.nombre,

                "stock_actual":
                    variante.stock,

                "stock_minimo":
                    variante.stock_minimo,

                "necesita_reposicion":
                    True
            }
        )

    return data


# ============================================================
# CORTES DE CAJA
# ============================================================

def reporte_cortes(
    fecha_inicio=None,
    fecha_fin=None
):

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

    if fecha_inicio:

        cortes = cortes.filter(
            fecha_inicio__date__gte=fecha_inicio
        )

    if fecha_fin:

        cortes = cortes.filter(
            fecha_inicio__date__lte=fecha_fin
        )

    data = []

    for corte in cortes:

        data.append(
            {
                "id": corte.id,

                "caja":
                    str(corte.caja),

                "usuario": (
                    f"{corte.usuario.nombre} "
                    f"{corte.usuario.apellido}"
                ),

                "fecha_inicio":
                    corte.fecha_inicio,

                "fecha_fin":
                    corte.fecha_fin,

                "efectivo_inicial":
                    dinero(
                        corte.efectivo_inicial
                    ),

                "efectivo_final": (
                    dinero(
                        corte.efectivo_final
                    )
                    if corte.efectivo_final is not None
                    else None
                ),

                "diferencia": (
                    dinero(
                        corte.diferencia
                    )
                    if corte.diferencia is not None
                    else None
                )
            }
        )

    return data


# ============================================================
# DEVOLUCIONES
# ============================================================

def reporte_devoluciones(
    fecha_inicio=None,
    fecha_fin=None
):

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

    if fecha_inicio:

        devoluciones = devoluciones.filter(
            fecha__date__gte=fecha_inicio
        )

    if fecha_fin:

        devoluciones = devoluciones.filter(
            fecha__date__lte=fecha_fin
        )

    data = []

    for devolucion in devoluciones:

        productos = []

        for detalle in (
            devolucion.detalles.all()
        ):

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

                    "cantidad":
                        detalle.cantidad,

                    "subtotal":
                        dinero(
                            detalle.subtotal
                        )
                }
            )

        data.append(
            {
                "id":
                    devolucion.id,

                "venta_folio":
                    devolucion.venta.folio,

                "usuario": (
                    f"{devolucion.usuario.nombre} "
                    f"{devolucion.usuario.apellido}"
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

                "productos":
                    productos,

                "fecha":
                    devolucion.fecha
            }
        )

    return data


# ============================================================
# GARANTÍAS
# ============================================================

def reporte_garantias(
    fecha_inicio=None,
    fecha_fin=None,
    estado=None
):

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

    if fecha_inicio:

        garantias = garantias.filter(
            fecha__date__gte=fecha_inicio
        )

    if fecha_fin:

        garantias = garantias.filter(
            fecha__date__lte=fecha_fin
        )

    if estado:

        garantias = garantias.filter(
            estado=estado
        )

    data = []

    for garantia in garantias:

        data.append(
            {
                "id":
                    garantia.id,

                "venta_folio":
                    garantia.venta.folio,

                "producto": (
                    garantia
                    .variante
                    .producto
                    .nombre
                ),

                "variante": (
                    garantia
                    .variante
                    .nombre
                ),

                "variante_nueva": (
                    garantia
                    .variante_nueva
                    .nombre
                    if garantia.variante_nueva
                    else None
                ),

                "cantidad":
                    garantia.cantidad,

                "usuario": (
                    f"{garantia.usuario.nombre} "
                    f"{garantia.usuario.apellido}"
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
                    garantia.fecha_actualizacion
            }
        )

    return data


# ============================================================
# MOVIMIENTOS DE INVENTARIO
# ============================================================

def reporte_movimientos(
    fecha_inicio=None,
    fecha_fin=None,
    tipo=None
):

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

    if fecha_inicio:

        movimientos = movimientos.filter(
            fecha__date__gte=fecha_inicio
        )

    if fecha_fin:

        movimientos = movimientos.filter(
            fecha__date__lte=fecha_fin
        )

    if tipo:

        movimientos = movimientos.filter(
            tipo=tipo
        )

    data = []

    for movimiento in movimientos:

        data.append(
            {
                "id":
                    movimiento.id,

                "producto": (
                    movimiento
                    .variante
                    .producto
                    .nombre
                ),

                "variante": (
                    movimiento
                    .variante
                    .nombre
                ),

                "tipo":
                    movimiento.tipo,

                "stock_anterior":
                    movimiento.stock_anterior,

                "cantidad":
                    movimiento.cantidad,

                "stock_nuevo":
                    movimiento.stock_nuevo,

                "observaciones":
                    movimiento.observaciones,

                "usuario": (
                    f"{movimiento.usuario.nombre} "
                    f"{movimiento.usuario.apellido}"
                ),

                "fecha":
                    movimiento.fecha
            }
        )

    return data