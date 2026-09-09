from decimal import Decimal, ROUND_HALF_UP

from django.db import models, transaction
from django.utils import timezone

from ventas.models import Venta
from empresa.models import Empresa
from detalle_venta.models import DetalleVenta
from inventario.models import MovimientoInventario
from corte_caja.models import MovimientoCaja, CorteCaja
from garantias.models import Garantia
from variantes.models import Variante
from bitacora.services import registrar_bitacora
from config.exceptions import BusinessException

from .models import Devolucion, DetalleDevolucion


_Q = Decimal("0.01")


def _redondear(valor):
    return valor.quantize(
        _Q,
        rounding=ROUND_HALF_UP
    )


# ============================================================
# HELPERS CREAR DEVOLUCIÓN
# ============================================================

def _validar_venta_devolucion(venta_id):

    try:

        venta = (
            Venta.objects
            .select_for_update()
            .get(id=venta_id)
        )

    except Venta.DoesNotExist:

        raise BusinessException(
            "La venta no existe."
        )

    if venta.estado == "CANCELADA":

        raise BusinessException(
            "No se puede devolver una venta cancelada."
        )

    if venta.estado == "DEVUELTA":

        raise BusinessException(
            "La venta ya fue devuelta completamente."
        )

    return venta


def _validar_plazo(venta, tipo):

    if tipo != "NORMAL":
        return

    empresa = Empresa.objects.first()

    if not empresa:

        raise BusinessException(
            "No existe configuración de empresa."
        )

    if (
        timezone.now() - venta.fecha
    ).days > empresa.dias_devolucion:

        raise BusinessException(
            "El periodo de devolución expiró."
        )


def _calcular_factor_reembolso(venta):

    subtotal_bruto = (
        DetalleVenta.objects
        .filter(venta=venta)
        .aggregate(
            total=models.Sum("subtotal")
        )["total"]
        or Decimal("0.00")
    )

    subtotal_bruto = _redondear(
        subtotal_bruto
    )

    if subtotal_bruto <= 0:

        raise BusinessException(
            "La venta no tiene un subtotal válido."
        )

    return venta.subtotal / subtotal_bruto


def _disponible_para_devolucion(
    detalle_venta
):

    cantidad_devuelta = (
        DetalleDevolucion.objects
        .filter(
            detalle_venta=detalle_venta,
            devolucion__estado__in=[
                "PENDIENTE",
                "APROBADA"
            ]
        )
        .aggregate(
            total=models.Sum("cantidad")
        )["total"]
        or 0
    )

    cantidad_garantizada = (
        Garantia.objects
        .filter(
            detalle_venta=detalle_venta,
            estado__in=[
                "PENDIENTE",
                "APROBADA",
            ]
        )
        .aggregate(
            total=models.Sum("cantidad")
        )["total"]
        or 0
    )

    return max(
        detalle_venta.cantidad
        - cantidad_devuelta
        - cantidad_garantizada,
        0
    )


def _crear_detalles_devolucion(
    devolucion,
    venta,
    productos,
    factor_reembolso
):

    total = Decimal("0.00")

    for item in productos:

        try:

            detalle_venta = (
                DetalleVenta.objects
                .select_for_update()
                .get(
                    id=item["detalle_venta_id"],
                    venta=venta
                )
            )

        except DetalleVenta.DoesNotExist:

            raise BusinessException(
                "El producto no pertenece a la venta."
            )

        cantidad = item["cantidad"]

        if cantidad <= 0:

            raise BusinessException(
                "La cantidad debe ser mayor a cero."
            )

        disponible = (
            _disponible_para_devolucion(
                detalle_venta
            )
        )

        if cantidad > disponible:

            raise BusinessException(
                "La cantidad solicitada para devolución "
                "supera las unidades disponibles. "
                f"Disponibles: {disponible}."
            )

        subtotal_bruto = _redondear(
            cantidad * detalle_venta.precio_unitario
        )

        subtotal = _redondear(
            subtotal_bruto * factor_reembolso
        )

        DetalleDevolucion.objects.create(
            devolucion=devolucion,
            detalle_venta=detalle_venta,
            cantidad=cantidad,
            precio_original=detalle_venta.precio_unitario,
            subtotal=subtotal,
        )

        total += subtotal

    return _redondear(total)


def _calcular_total_devuelto(
    venta,
    total
):

    if total <= 0:

        raise BusinessException(
            "El importe de la devolución debe ser mayor que cero."
        )

    if venta.subtotal > 0:

        iva_devolucion = _redondear(
            (total * venta.iva) / venta.subtotal
        )

    else:

        iva_devolucion = Decimal("0.00")

    total_devuelto = _redondear(
        total + iva_devolucion
    )

    return min(
        total_devuelto,
        venta.total
    )


# ============================================================
# HELPERS APROBAR DEVOLUCIÓN
# ============================================================

def _validar_cantidades_aprobacion(
    detalles,
    devolucion
):

    for detalle in detalles:

        detalle_venta = detalle.detalle_venta

        cantidad_aprobada = (
            DetalleDevolucion.objects
            .filter(
                detalle_venta=detalle_venta,
                devolucion__estado="APROBADA"
            )
            .aggregate(
                total=models.Sum("cantidad")
            )["total"]
            or 0
        )

        cantidad_pendiente = (
            DetalleDevolucion.objects
            .filter(
                detalle_venta=detalle_venta,
                devolucion__estado="PENDIENTE"
            )
            .exclude(
                devolucion=devolucion
            )
            .aggregate(
                total=models.Sum("cantidad")
            )["total"]
            or 0
        )

        cantidad_garantizada = (
            Garantia.objects
            .filter(
                detalle_venta=detalle_venta,
                estado__in=[
                    "PENDIENTE",
                    "APROBADA",
                ]
            )
            .aggregate(
                total=models.Sum("cantidad")
            )["total"]
            or 0
        )

        disponible = max(
            detalle_venta.cantidad
            - cantidad_aprobada
            - cantidad_pendiente
            - cantidad_garantizada,
            0
        )

        if detalle.cantidad > disponible:

            raise BusinessException(
                "La cantidad devuelta supera "
                "la cantidad disponible."
            )


def _obtener_corte_efectivo(venta):

    if not venta.corte_caja:

        raise BusinessException(
            "La venta no tiene un corte de caja asociado."
        )

    corte = (
        CorteCaja.objects
        .select_for_update()
        .filter(
            caja=venta.corte_caja.caja,
            fecha_fin__isnull=True
        )
        .first()
    )

    if not corte:

        raise BusinessException(
            "No existe un corte de caja abierto "
            "para registrar el reembolso."
        )

    return corte


def _reponer_stock(
    detalles,
    devolucion,
    usuario
):

    for detalle in detalles:

        variante = (
            Variante.objects
            .select_for_update()
            .get(
                id=detalle.detalle_venta.variante_id
            )
        )

        stock_ant = variante.stock
        stock_def_ant = variante.stock_defectuoso

        if devolucion.tipo == "DEFECTUOSO":

            stock_nuevo = stock_ant

            stock_def_nuevo = (
                stock_def_ant
                + detalle.cantidad
            )

        else:

            stock_nuevo = (
                stock_ant
                + detalle.cantidad
            )

            stock_def_nuevo = stock_def_ant

        MovimientoInventario.objects.create(
            variante=variante,
            tipo="DEVOLUCION",
            stock_anterior=stock_ant,
            cantidad=detalle.cantidad,
            stock_nuevo=stock_nuevo,
            stock_defectuoso_anterior=stock_def_ant,
            stock_defectuoso_nuevo=stock_def_nuevo,
            observaciones=(
                f"Devolución {devolucion.id}"
            ),
            usuario=usuario,
        )

        variante.stock = stock_nuevo
        variante.stock_defectuoso = stock_def_nuevo

        variante.save(
            update_fields=[
                "stock",
                "stock_defectuoso",
                "fecha_actualizacion"
            ]
        )


def _venta_completamente_devuelta(venta):

    for detalle_venta in venta.detalles.all():

        devuelto = (
            DetalleDevolucion.objects
            .filter(
                detalle_venta=detalle_venta,
                devolucion__estado="APROBADA"
            )
            .aggregate(
                total=models.Sum("cantidad")
            )["total"]
            or 0
        )

        if devuelto < detalle_venta.cantidad:

            return False

    return True


# ============================================================
# CREAR DEVOLUCIÓN
# ============================================================

@transaction.atomic
def crear_devolucion(
    data,
    usuario
):

    venta = _validar_venta_devolucion(
        data["venta_id"]
    )

    _validar_plazo(
        venta,
        data["tipo"]
    )

    # ========================================================
    # MÉTODO DE REEMBOLSO AUTOMÁTICO
    # ========================================================

    metodo_pago_reembolso = venta.metodo_pago

    if not metodo_pago_reembolso:

        raise BusinessException(
            "La venta no tiene un método de pago asociado."
        )

    factor_reembolso = (
        _calcular_factor_reembolso(
            venta
        )
    )

    devolucion = Devolucion.objects.create(
        venta=venta,
        usuario=usuario,
        metodo_pago_reembolso=metodo_pago_reembolso,
        tipo=data["tipo"],
        motivo=data["motivo"],
        estado="PENDIENTE",
    )

    total = _crear_detalles_devolucion(
        devolucion,
        venta,
        data["productos"],
        factor_reembolso
    )

    devolucion.total_devuelto = (
        _calcular_total_devuelto(
            venta,
            total
        )
    )

    devolucion.save(
        update_fields=[
            "total_devuelto"
        ]
    )

    registrar_bitacora(
        usuario=usuario,
        modulo="Devoluciones",
        accion="DEVOLUCION_CREADA",
        descripcion=(
            f"Devolución '{devolucion.id}' creada "
            f"para la venta '{venta.folio}' por "
            f"{usuario.nombre} {usuario.apellido}. "
            f"Tipo: {devolucion.tipo}. "
            f"Motivo: {devolucion.motivo}. "
            f"Total devuelto: "
            f"${devolucion.total_devuelto:.2f}. "
            f"Método de reembolso: "
            f"{metodo_pago_reembolso.nombre}. "
            f"Estado: PENDIENTE."
        ),
    )

    return devolucion


# ============================================================
# APROBAR DEVOLUCIÓN
# ============================================================

@transaction.atomic
def aprobar_devolucion(
    devolucion_id,
    usuario
):

    try:

        devolucion = (
            Devolucion.objects
            .select_for_update()
            .get(id=devolucion_id)
        )

    except Devolucion.DoesNotExist:

        raise BusinessException(
            "La devolución no existe."
        )

    if devolucion.estado != "PENDIENTE":

        raise BusinessException(
            "Solo se pueden aprobar devoluciones pendientes."
        )

    try:

        venta = (
            Venta.objects
            .select_for_update()
            .get(id=devolucion.venta_id)
        )

    except Venta.DoesNotExist:

        raise BusinessException(
            "La venta asociada no existe."
        )

    if venta.estado == "CANCELADA":

        raise BusinessException(
            "No se puede aprobar una devolución "
            "de una venta cancelada."
        )

    if venta.estado == "DEVUELTA":

        raise BusinessException(
            "La venta ya fue devuelta completamente."
        )

    if not devolucion.metodo_pago_reembolso:

        raise BusinessException(
            "La devolución no tiene un método de reembolso."
        )

    metodo_pago = (
        devolucion.metodo_pago_reembolso
    )

    detalles = list(
        devolucion.detalles
        .select_related("detalle_venta")
    )

    if not detalles:

        raise BusinessException(
            "La devolución no tiene productos."
        )

    _validar_cantidades_aprobacion(
        detalles,
        devolucion
    )

    # ========================================================
    # DETERMINAR CORTE PARA EL REEMBOLSO
    # ========================================================

    if metodo_pago.nombre == "EFECTIVO":

        corte = _obtener_corte_efectivo(
            venta
        )

    else:

        corte = venta.corte_caja

        if not corte:

            raise BusinessException(
                "La venta no tiene un corte de caja asociado."
            )

    # ========================================================
    # REPONER STOCK
    # ========================================================

    _reponer_stock(
        detalles,
        devolucion,
        usuario
    )

    # ========================================================
    # REGISTRAR REEMBOLSO
    # ========================================================

    MovimientoCaja.objects.create(
        corte_caja=corte,
        metodo_pago=metodo_pago,
        tipo="REEMBOLSO",
        monto=devolucion.total_devuelto,
        devolucion=devolucion,
        observaciones=(
            f"Reembolso de devolución "
            f"{devolucion.id}"
        ),
        usuario=usuario,
    )

    # ========================================================
    # ACTUALIZAR DEVOLUCIÓN
    # ========================================================

    devolucion.estado = "APROBADA"

    devolucion.save(
        update_fields=[
            "estado"
        ]
    )

    # ========================================================
    # BITÁCORA
    # ========================================================

    registrar_bitacora(
        usuario=usuario,
        modulo="Devoluciones",
        accion="DEVOLUCION_APROBADA",
        descripcion=(
            f"Devolución '{devolucion.id}' "
            f"aprobada por "
            f"{usuario.nombre} "
            f"{usuario.apellido}. "
            f"Venta: '{venta.folio}'. "
            f"Total devuelto: "
            f"${devolucion.total_devuelto:.2f}. "
            f"Método de reembolso: "
            f"{metodo_pago.nombre}."
        ),
    )

    # ========================================================
    # MARCAR VENTA COMO DEVUELTA
    # ========================================================

    if _venta_completamente_devuelta(venta):

        venta.estado = "DEVUELTA"

        venta.save(
            update_fields=[
                "estado"
            ]
        )

    return devolucion


# ============================================================
# RECHAZAR DEVOLUCIÓN
# ============================================================

@transaction.atomic
def cambiar_estado_devolucion(
    devolucion_id,
    nuevo_estado,
    usuario
):

    try:

        devolucion = (
            Devolucion.objects
            .select_for_update()
            .get(id=devolucion_id)
        )

    except Devolucion.DoesNotExist:

        raise BusinessException(
            "La devolución no existe."
        )

    if devolucion.estado != "PENDIENTE":

        raise BusinessException(
            "Solo se pueden modificar devoluciones pendientes."
        )

    if nuevo_estado != "RECHAZADA":

        raise BusinessException(
            "Para aprobar una devolución debe "
            "utilizarse el proceso de aprobación."
        )

    devolucion.estado = "RECHAZADA"

    devolucion.save(
        update_fields=[
            "estado"
        ]
    )

    registrar_bitacora(
        usuario=usuario,
        modulo="Devoluciones",
        accion="DEVOLUCION_RECHAZADA",
        descripcion=(
            f"Devolución '{devolucion.id}' "
            f"rechazada por "
            f"{usuario.nombre} "
            f"{usuario.apellido}. "
            f"Venta: '{devolucion.venta.folio}'. "
            f"Motivo registrado: "
            f"{devolucion.motivo}."
        ),
    )

    return devolucion