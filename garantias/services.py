from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from ventas.models import Venta
from detalle_venta.models import DetalleVenta
from variantes.models import Variante
from inventario.models import MovimientoInventario

from devoluciones.models import (
    Devolucion,
    DetalleDevolucion
)

from bitacora.services import registrar_bitacora
from config.exceptions import BusinessException

from .models import Garantia


# ============================================================
# CREAR GARANTÍA
# ============================================================

@transaction.atomic
def crear_garantia(
    data,
    usuario
):

    # ========================================================
    # 1. Buscar y bloquear la venta
    # ========================================================

    try:

        venta = (
            Venta.objects
            .select_for_update()
            .get(
                id=data["venta_id"]
            )
        )

    except Venta.DoesNotExist:

        raise BusinessException(
            "La venta no existe."
        )

    # ========================================================
    # 2. Validar estado de la venta
    # ========================================================

    if venta.estado == "CANCELADA":

        raise BusinessException(
            "No se puede crear una garantía para una venta cancelada."
        )

    if venta.estado == "DEVUELTA":

        raise BusinessException(
            "No se puede crear una garantía para una venta devuelta."
        )

    # ========================================================
    # 3. Buscar variante
    # ========================================================

    try:

        variante = (
            Variante.objects
            .get(
                id=data["variante_id"]
            )
        )

    except Variante.DoesNotExist:

        raise BusinessException(
            "La variante no existe."
        )

    # ========================================================
    # 4. Buscar y bloquear detalle de venta
    # ========================================================

    try:

        detalle_venta = (
            DetalleVenta.objects
            .select_for_update()
            .get(
                id=data["detalle_venta_id"],
                venta=venta
            )
        )

    except DetalleVenta.DoesNotExist:

        raise BusinessException(
            "El detalle de venta no existe o no pertenece a la venta indicada."
        )

    variante = detalle_venta.variante

    if str(variante.id) != str(data["variante_id"]):

        raise BusinessException(
            "La variante no corresponde al detalle de venta."
        )

    # ========================================================
    # 5. Validar cantidad
    # ========================================================

    cantidad = data["cantidad"]

    if cantidad <= 0:

        raise BusinessException(
            "La cantidad debe ser mayor que cero."
        )

    if cantidad > detalle_venta.cantidad:

        raise BusinessException(
            "La cantidad solicitada para garantía "
            "no puede superar la cantidad vendida."
        )

    # ========================================================
    # 6. Validar garantía configurada
    # ========================================================

    if not variante.garantia_meses:

        raise BusinessException(
            "Este producto no tiene garantía configurada."
        )

    # ========================================================
    # 7. Validar vigencia
    # ========================================================

    fecha_limite = (
        venta.fecha
        + relativedelta(
            months=variante.garantia_meses
        )
    )

    if timezone.now() > fecha_limite:

        raise BusinessException(
            "La garantía de este producto venció el "
            f"{fecha_limite.strftime('%d/%m/%Y')}."
        )

    # ========================================================
    # 8. CALCULAR UNIDADES DISPONIBLES
    #
    # cantidad vendida
    # - devoluciones pendientes/aprobadas
    # - garantías pendientes/aprobadas/finalizadas
    # ========================================================

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

    cantidad_devuelta = (
        DetalleDevolucion.objects
        .filter(
            detalle_venta=detalle_venta,
            devolucion__estado__in=[
                "PENDIENTE",
                "APROBADA",
            ]
        )
        .aggregate(
            total=Sum("cantidad")
        )["total"]
        or 0
    )

    cantidad_disponible = (
        detalle_venta.cantidad
        -
        cantidad_garantizada
        -
        cantidad_devuelta
    )

    if cantidad_disponible < 0:

        cantidad_disponible = 0

    if cantidad > cantidad_disponible:

        raise BusinessException(
            "La cantidad solicitada supera las unidades "
            "disponibles para garantía. "
            f"Disponibles: {cantidad_disponible}."
        )

    # ========================================================
    # 9. CREAR GARANTÍA
    # ========================================================

    garantia = Garantia.objects.create(

        venta=venta,

        detalle_venta=detalle_venta,

        variante=variante,

        cantidad=cantidad,

        usuario=usuario,

        motivo=data["motivo"],

        estado="PENDIENTE"

    )

    # ========================================================
    # BITÁCORA
    # ========================================================

    registrar_bitacora(

        usuario=usuario,

        modulo="Garantias",

        accion="CREAR_GARANTIA",

        descripcion=(
            f"Garantía {garantia.id} registrada "
            f"para la venta '{venta.folio}' por "
            f"{usuario.nombre} "
            f"{usuario.apellido}. "
            f"Variante: '{variante.nombre}'. "
            f"Cantidad: {cantidad}. "
            f"Motivo: {garantia.motivo}."
        )

    )

    return garantia


# ============================================================
# APROBAR GARANTÍA
# ============================================================

@transaction.atomic
def aprobar_garantia(
    garantia_id,
    data,
    usuario
):

    # ========================================================
    # 1. Buscar y bloquear garantía
    # ========================================================

    try:

        garantia = (
            Garantia.objects
            .select_for_update()
            .select_related(
                "venta",
                "detalle_venta",
                "variante"
            )
            .get(
                id=garantia_id
            )
        )

    except Garantia.DoesNotExist:

        raise BusinessException(
            "La garantía no existe."
        )

    # ========================================================
    # 2. Validar estado
    # ========================================================

    if garantia.estado != "PENDIENTE":

        raise BusinessException(
            "Solo se pueden aprobar garantías pendientes."
        )

    resolucion = data["resolucion"]

    observaciones = data.get(
        "observaciones"
    )

    cantidad = garantia.cantidad

    # ========================================================
    # 3. REEMPLAZO
    # ========================================================

    if resolucion == "REEMPLAZO":

        variante = (
            Variante.objects
            .select_for_update()
            .get(
                id=garantia.variante_id
            )
        )

        # ----------------------------------------------------
        # Verificar stock vendible
        # ----------------------------------------------------

        if variante.stock < cantidad:

            raise BusinessException(
                "Stock insuficiente para realizar el reemplazo. "
                f"Stock disponible: {variante.stock}. "
                f"Cantidad requerida: {cantidad}."
            )

        # ----------------------------------------------------
        # STOCK ORIGINAL
        # ----------------------------------------------------

        stock_anterior = variante.stock

        stock_defectuoso_anterior = (
            variante.stock_defectuoso
        )

        # ----------------------------------------------------
        # RECIBIR PRODUCTO DEFECTUOSO
        #
        # NO aumenta el stock vendible.
        # Aumenta stock_defectuoso.
        # ----------------------------------------------------

        stock_nuevo = stock_anterior

        stock_defectuoso_nuevo = (
            stock_defectuoso_anterior
            + cantidad
        )

        variante.stock = stock_nuevo

        variante.stock_defectuoso = (
            stock_defectuoso_nuevo
        )

        variante.save(
            update_fields=[
                "stock",
                "stock_defectuoso",
                "fecha_actualizacion"
            ]
        )

        MovimientoInventario.objects.create(

            variante=variante,

            tipo="GARANTIA",

            stock_anterior=stock_anterior,

            cantidad=cantidad,

            stock_nuevo=stock_nuevo,

            stock_defectuoso_anterior=(
                stock_defectuoso_anterior
            ),

            stock_defectuoso_nuevo=(
                stock_defectuoso_nuevo
            ),

            observaciones=(
                f"Reemplazo por garantía "
                f"{garantia.id} - "
                "entrada producto defectuoso"
            ),

            usuario=usuario

        )

        # ----------------------------------------------------
        # ENTREGAR PRODUCTO NUEVO
        #
        # Disminuye solamente stock vendible.
        # ----------------------------------------------------

        stock_anterior = variante.stock

        stock_nuevo = (
            stock_anterior
            - cantidad
        )

        stock_defectuoso_actual = (
            variante.stock_defectuoso
        )

        variante.stock = stock_nuevo

        variante.save(
            update_fields=[
                "stock",
                "fecha_actualizacion"
            ]
        )

        MovimientoInventario.objects.create(

            variante=variante,

            tipo="GARANTIA",

            stock_anterior=stock_anterior,

            cantidad=cantidad,

            stock_nuevo=stock_nuevo,

            stock_defectuoso_anterior=(
                stock_defectuoso_actual
            ),

            stock_defectuoso_nuevo=(
                stock_defectuoso_actual
            ),

            observaciones=(
                f"Reemplazo por garantía "
                f"{garantia.id} - "
                "salida producto nuevo"
            ),

            usuario=usuario

        )

    # ========================================================
    # 4. CAMBIO_PRODUCTO
    # ========================================================

    elif resolucion == "CAMBIO_PRODUCTO":

        variante_nueva_id = data.get(
            "variante_nueva_id"
        )

        if not variante_nueva_id:

            raise BusinessException(
                "Debe especificar la variante nueva."
            )

        # ----------------------------------------------------
        # Bloquear variante original
        # ----------------------------------------------------

        variante_original = (
            Variante.objects
            .select_for_update()
            .get(
                id=garantia.variante_id
            )
        )

        # ----------------------------------------------------
        # Bloquear variante nueva
        # ----------------------------------------------------

        try:

            variante_nueva = (
                Variante.objects
                .select_for_update()
                .get(
                    id=variante_nueva_id
                )
            )

        except Variante.DoesNotExist:

            raise BusinessException(
                "La variante nueva no existe."
            )

        # ----------------------------------------------------
        # No permitir misma variante
        # ----------------------------------------------------

        if variante_original.id == variante_nueva.id:

            raise BusinessException(
                "La variante nueva debe ser diferente "
                "a la variante original."
            )

        # ----------------------------------------------------
        # Validar stock de variante nueva
        # ----------------------------------------------------

        if variante_nueva.stock < cantidad:

            raise BusinessException(
                "Stock insuficiente en la variante nueva "
                "para realizar el cambio. "
                f"Stock disponible: {variante_nueva.stock}. "
                f"Cantidad requerida: {cantidad}."
            )

        # ----------------------------------------------------
        # PRODUCTO ORIGINAL DEFECTUOSO REGRESA
        #
        # NO aumenta stock vendible.
        # Aumenta stock_defectuoso.
        # ----------------------------------------------------

        stock_original_anterior = (
            variante_original.stock
        )

        stock_original_defectuoso_anterior = (
            variante_original.stock_defectuoso
        )

        stock_original_nuevo = (
            stock_original_anterior
        )

        stock_original_defectuoso_nuevo = (
            stock_original_defectuoso_anterior
            + cantidad
        )

        variante_original.stock = (
            stock_original_nuevo
        )

        variante_original.stock_defectuoso = (
            stock_original_defectuoso_nuevo
        )

        variante_original.save(
            update_fields=[
                "stock",
                "stock_defectuoso",
                "fecha_actualizacion",
            ]
        )

        MovimientoInventario.objects.create(

            variante=variante_original,

            tipo="CAMBIO_PRODUCTO",

            stock_anterior=(
                stock_original_anterior
            ),

            cantidad=cantidad,

            stock_nuevo=(
                stock_original_nuevo
            ),

            stock_defectuoso_anterior=(
                stock_original_defectuoso_anterior
            ),

            stock_defectuoso_nuevo=(
                stock_original_defectuoso_nuevo
            ),

            observaciones=(
                f"Cambio de producto por garantía "
                f"{garantia.id} - "
                "entrada producto original defectuoso"
            ),

            usuario=usuario

        )

        # ----------------------------------------------------
        # PRODUCTO NUEVO SALE
        # ----------------------------------------------------

        stock_nueva_anterior = (
            variante_nueva.stock
        )

        stock_nueva_nuevo = (
            stock_nueva_anterior
            - cantidad
        )

        stock_nueva_defectuoso = (
            variante_nueva.stock_defectuoso
        )

        variante_nueva.stock = (
            stock_nueva_nuevo
        )

        variante_nueva.save(
            update_fields=[
                "stock",
                "fecha_actualizacion",
            ]
        )

        MovimientoInventario.objects.create(

            variante=variante_nueva,

            tipo="CAMBIO_PRODUCTO",

            stock_anterior=(
                stock_nueva_anterior
            ),

            cantidad=cantidad,

            stock_nuevo=(
                stock_nueva_nuevo
            ),

            stock_defectuoso_anterior=(
                stock_nueva_defectuoso
            ),

            stock_defectuoso_nuevo=(
                stock_nueva_defectuoso
            ),

            observaciones=(
                f"Cambio de producto por garantía "
                f"{garantia.id} - "
                "salida producto nuevo"
            ),

            usuario=usuario

        )

        garantia.variante_nueva = (
            variante_nueva
        )

    # ========================================================
    # 5. REPARACION
    # ========================================================

    elif resolucion == "REPARACION":

        # La reparación no modifica stock.
        pass

    # ========================================================
    # 6. ACTUALIZAR GARANTÍA
    # ========================================================

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

    # ========================================================
    # BITÁCORA
    # ========================================================

    registrar_bitacora(

        usuario=usuario,

        modulo="Garantias",

        accion="APROBAR_GARANTIA",

        descripcion=(
            f"Garantía {garantia.id} aprobada por "
            f"{usuario.nombre} "
            f"{usuario.apellido}. "
            f"Venta: '{garantia.venta.folio}'. "
            f"Variante: '{garantia.variante.nombre}'. "
            f"Cantidad: {cantidad}. "
            f"Resolución: {resolucion}."
        )

    )

    return garantia


# ============================================================
# RECHAZAR GARANTÍA
# ============================================================

@transaction.atomic
def rechazar_garantia(
    garantia_id,
    data,
    usuario
):

    # ========================================================
    # 1. Buscar y bloquear
    # ========================================================

    try:

        garantia = (
            Garantia.objects
            .select_for_update()
            .get(
                id=garantia_id
            )
        )

    except Garantia.DoesNotExist:

        raise BusinessException(
            "La garantía no existe."
        )

    # ========================================================
    # 2. Validar estado
    # ========================================================

    if garantia.estado != "PENDIENTE":

        raise BusinessException(
            "Solo se pueden rechazar garantías pendientes."
        )

    # ========================================================
    # 3. Rechazar
    # ========================================================

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

    # ========================================================
    # BITÁCORA
    # ========================================================

    registrar_bitacora(

        usuario=usuario,

        modulo="Garantias",

        accion="RECHAZAR_GARANTIA",

        descripcion=(
            f"Garantía {garantia.id} rechazada por "
            f"{usuario.nombre} "
            f"{usuario.apellido}. "
            f"Venta: '{garantia.venta.folio}'. "
            f"Variante: '{garantia.variante.nombre}'. "
            f"Cantidad: {garantia.cantidad}. "
            f"Observaciones: "
            f"{garantia.observaciones or 'Sin observaciones'}."
        )

    )

    return garantia


# ============================================================
# FINALIZAR GARANTÍA
# ============================================================

@transaction.atomic
def finalizar_garantia(
    garantia_id,
    data,
    usuario
):

    # ========================================================
    # 1. Buscar y bloquear
    # ========================================================

    try:

        garantia = (
            Garantia.objects
            .select_for_update()
            .get(
                id=garantia_id
            )
        )

    except Garantia.DoesNotExist:

        raise BusinessException(
            "La garantía no existe."
        )

    # ========================================================
    # 2. Validar estado
    # ========================================================

    if garantia.estado != "APROBADA":

        raise BusinessException(
            "Solo se pueden finalizar garantías aprobadas."
        )

    # ========================================================
    # 3. Finalizar
    # ========================================================

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

    # ========================================================
    # BITÁCORA
    # ========================================================

    registrar_bitacora(

        usuario=usuario,

        modulo="Garantias",

        accion="FINALIZAR_GARANTIA",

        descripcion=(
            f"Garantía {garantia.id} finalizada por "
            f"{usuario.nombre} "
            f"{usuario.apellido}. "
            f"Venta: '{garantia.venta.folio}'. "
            f"Variante: '{garantia.variante.nombre}'. "
            f"Cantidad: {garantia.cantidad}. "
            f"Resolución: "
            f"{garantia.resolucion or 'No especificada'}."
        )

    )

    return garantia