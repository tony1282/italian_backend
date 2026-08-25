from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from ventas.models import Venta
from detalle_venta.models import DetalleVenta
from variantes.models import Variante
from inventario.models import MovimientoInventario

from .models import Garantia


@transaction.atomic
def crear_garantia(data, usuario):

    # ============================================================
    # 1. Buscar y bloquear la venta
    # ============================================================

    try:
        venta = (
            Venta.objects
            .select_for_update()
            .get(id=data["venta_id"])
        )
    except Venta.DoesNotExist:
        raise Exception("La venta no existe.")

    # ============================================================
    # 2. Validar estado de la venta
    # ============================================================

    if venta.estado == "CANCELADA":
        raise Exception(
            "No se puede crear una garantía para una venta cancelada."
        )

    if venta.estado == "DEVUELTA":
        raise Exception(
            "No se puede crear una garantía para una venta devuelta."
        )

    # ============================================================
    # 3. Buscar variante
    # ============================================================

    try:
        variante = Variante.objects.get(
            id=data["variante_id"]
        )
    except Variante.DoesNotExist:
        raise Exception("La variante no existe.")

    # ============================================================
    # 4. Buscar y bloquear el detalle de venta
    # ============================================================

    try:
        detalle_venta = (
            DetalleVenta.objects
            .select_for_update()
            .get(
                venta=venta,
                variante=variante
            )
        )
    except DetalleVenta.DoesNotExist:
        raise Exception(
            "La variante no pertenece a la venta indicada."
        )

    # ============================================================
    # 5. Validar cantidad
    # ============================================================

    cantidad = data["cantidad"]

    if cantidad > detalle_venta.cantidad:
        raise Exception(
            "La cantidad solicitada para garantía "
            "no puede superar la cantidad vendida."
        )

    # ============================================================
    # 6. Validar que tenga garantía configurada
    # ============================================================

    if not variante.garantia_meses:
        raise Exception(
            "Este producto no tiene garantía configurada."
        )

    # ============================================================
    # 7. Validar vigencia de la garantía
    # ============================================================

    fecha_limite = (
        venta.fecha
        + relativedelta(months=variante.garantia_meses)
    )

    if timezone.now() > fecha_limite:
        raise Exception(
            "La garantía de este producto venció el "
            f"{fecha_limite.strftime('%d/%m/%Y')}."
        )

    # ============================================================
    # 8. Calcular cantidad ya utilizada en garantías
    #
    # PENDIENTE y APROBADA reservan unidades.
    #
    # RECHAZADA no cuenta porque no consumió una garantía.
    # FINALIZADA sí cuenta porque la garantía ya fue atendida.
    # ============================================================

    cantidad_garantizada = (
        Garantia.objects
        .filter(
            detalle_venta=detalle_venta,
            estado__in=[
                "PENDIENTE",
                "APROBADA",
                "FINALIZADA",
            ]
        )
        .aggregate(
            total=Sum("cantidad")
        )["total"]
        or 0
    )

    cantidad_disponible = (
        detalle_venta.cantidad - cantidad_garantizada
    )

    if cantidad > cantidad_disponible:
        raise Exception(
            "La cantidad solicitada supera las unidades "
            f"disponibles para garantía. "
            f"Disponibles: {cantidad_disponible}."
        )

    # ============================================================
    # 9. Crear garantía
    # ============================================================

    garantia = Garantia.objects.create(
        venta=venta,
        detalle_venta=detalle_venta,
        variante=variante,
        cantidad=cantidad,
        usuario=usuario,
        motivo=data["motivo"],
        estado="PENDIENTE"
    )

    return garantia


@transaction.atomic
def aprobar_garantia(garantia_id, data, usuario):

    # ============================================================
    # 1. Buscar y bloquear garantía
    # ============================================================

    try:
        garantia = (
            Garantia.objects
            .select_for_update()
            .select_related(
                "venta",
                "detalle_venta",
                "variante"
            )
            .get(id=garantia_id)
        )
    except Garantia.DoesNotExist:
        raise Exception("La garantía no existe.")

    # ============================================================
    # 2. Validar estado
    # ============================================================

    if garantia.estado != "PENDIENTE":
        raise Exception(
            "Solo se pueden aprobar garantías pendientes."
        )

    resolucion = data["resolucion"]
    observaciones = data.get("observaciones")
    cantidad = garantia.cantidad

    # ============================================================
    # 3. REEMPLAZO
    # ============================================================

    if resolucion == "REEMPLAZO":

        variante = (
            Variante.objects
            .select_for_update()
            .get(id=garantia.variante_id)
        )

        # Primero verificamos que exista stock suficiente
        # para entregar las unidades nuevas.
        if variante.stock < cantidad:
            raise Exception(
                "Stock insuficiente para realizar el reemplazo. "
                f"Stock disponible: {variante.stock}. "
                f"Cantidad requerida: {cantidad}."
            )

        # --------------------------------------------------------
        # Producto defectuoso recibido
        # --------------------------------------------------------

        variante.stock += cantidad

        variante.save(
            update_fields=["stock"]
        )

        MovimientoInventario.objects.create(
            variante=variante,
            tipo="GARANTIA",
            cantidad=cantidad,
            observaciones=(
                f"Reemplazo por garantía {garantia.id} - "
                "entrada producto defectuoso"
            ),
            usuario=usuario
        )

        # --------------------------------------------------------
        # Producto nuevo entregado
        # --------------------------------------------------------

        variante.stock -= cantidad

        variante.save(
            update_fields=["stock"]
        )

        MovimientoInventario.objects.create(
            variante=variante,
            tipo="GARANTIA",
            cantidad=cantidad,
            observaciones=(
                f"Reemplazo por garantía {garantia.id} - "
                "salida producto nuevo"
            ),
            usuario=usuario
        )

    # ============================================================
    # 4. CAMBIO_PRODUCTO
    # ============================================================

    elif resolucion == "CAMBIO_PRODUCTO":

        variante_nueva_id = data.get(
            "variante_nueva_id"
        )

        if not variante_nueva_id:
            raise Exception(
                "Debe especificar la variante nueva."
            )

        # --------------------------------------------------------
        # Bloquear variante original
        # --------------------------------------------------------

        variante_original = (
            Variante.objects
            .select_for_update()
            .get(id=garantia.variante_id)
        )

        # --------------------------------------------------------
        # Bloquear variante nueva
        # --------------------------------------------------------

        try:
            variante_nueva = (
                Variante.objects
                .select_for_update()
                .get(id=variante_nueva_id)
            )
        except Variante.DoesNotExist:
            raise Exception(
                "La variante nueva no existe."
            )

        # --------------------------------------------------------
        # No permitir cambiar por la misma variante
        # --------------------------------------------------------

        if variante_original.id == variante_nueva.id:
            raise Exception(
                "La variante nueva debe ser diferente "
                "a la variante original."
            )

        # --------------------------------------------------------
        # Validar stock
        # --------------------------------------------------------

        if variante_nueva.stock < cantidad:
            raise Exception(
                "Stock insuficiente en la variante nueva "
                "para realizar el cambio. "
                f"Stock disponible: {variante_nueva.stock}. "
                f"Cantidad requerida: {cantidad}."
            )

        # --------------------------------------------------------
        # Producto original regresa
        # --------------------------------------------------------

        variante_original.stock += cantidad

        variante_original.save(
            update_fields=["stock"]
        )

        MovimientoInventario.objects.create(
            variante=variante_original,
            tipo="CAMBIO_PRODUCTO",
            cantidad=cantidad,
            observaciones=(
                f"Cambio de producto por garantía "
                f"{garantia.id} - entrada producto original"
            ),
            usuario=usuario
        )

        # --------------------------------------------------------
        # Producto nuevo sale
        # --------------------------------------------------------

        variante_nueva.stock -= cantidad

        variante_nueva.save(
            update_fields=["stock"]
        )

        MovimientoInventario.objects.create(
            variante=variante_nueva,
            tipo="CAMBIO_PRODUCTO",
            cantidad=cantidad,
            observaciones=(
                f"Cambio de producto por garantía "
                f"{garantia.id} - salida producto nuevo"
            ),
            usuario=usuario
        )

        garantia.variante_nueva = variante_nueva

    # ============================================================
    # 5. REPARACION
    # ============================================================

    elif resolucion == "REPARACION":

        # La reparación no modifica el stock.
        pass

    # ============================================================
    # 6. Actualizar garantía
    # ============================================================

    garantia.estado = "APROBADA"
    garantia.resolucion = resolucion
    garantia.observaciones = observaciones

    garantia.save(
        update_fields=[
            "estado",
            "resolucion",
            "observaciones",
            "variante_nueva_id",
            "fecha_actualizacion",
        ]
    )

    return garantia


@transaction.atomic
def rechazar_garantia(
    garantia_id,
    data,
    usuario
):

    # ============================================================
    # 1. Buscar y bloquear
    # ============================================================

    try:
        garantia = (
            Garantia.objects
            .select_for_update()
            .get(id=garantia_id)
        )
    except Garantia.DoesNotExist:
        raise Exception(
            "La garantía no existe."
        )

    # ============================================================
    # 2. Validar estado
    # ============================================================

    if garantia.estado != "PENDIENTE":
        raise Exception(
            "Solo se pueden rechazar garantías pendientes."
        )

    # ============================================================
    # 3. Rechazar
    # ============================================================

    garantia.estado = "RECHAZADA"
    garantia.observaciones = data.get(
        "observaciones"
    )

    garantia.save(
        update_fields=[
            "estado",
            "observaciones",
            "fecha_actualizacion",
        ]
    )

    return garantia


@transaction.atomic
def finalizar_garantia(
    garantia_id,
    data,
    usuario
):

    # ============================================================
    # 1. Buscar y bloquear
    # ============================================================

    try:
        garantia = (
            Garantia.objects
            .select_for_update()
            .get(id=garantia_id)
        )
    except Garantia.DoesNotExist:
        raise Exception(
            "La garantía no existe."
        )

    # ============================================================
    # 2. Validar estado
    # ============================================================

    if garantia.estado != "APROBADA":
        raise Exception(
            "Solo se pueden finalizar garantías aprobadas."
        )

    # ============================================================
    # 3. Finalizar
    # ============================================================

    garantia.estado = "FINALIZADA"

    if data.get("observaciones"):
        garantia.observaciones = data[
            "observaciones"
        ]

    garantia.save(
        update_fields=[
            "estado",
            "observaciones",
            "fecha_actualizacion",
        ]
    )

    return garantia