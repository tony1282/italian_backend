from decimal import Decimal, ROUND_HALF_UP

from django.db import models, transaction
from django.utils import timezone

from ventas.models import Venta
from empresa.models import Empresa
from detalle_venta.models import DetalleVenta

from inventario.models import MovimientoInventario
from metodos_pago.models import MetodoPago

from corte_caja.models import MovimientoCaja, CorteCaja

from garantias.models import Garantia

from .models import (
    Devolucion,
    DetalleDevolucion
)

from variantes.models import Variante

from bitacora.services import registrar_bitacora


# ==============================================================
# CREAR DEVOLUCIÓN
# ==============================================================

@transaction.atomic
def crear_devolucion(
    data,
    usuario
):

    venta_id = data["venta_id"]

    productos = data["productos"]

    # ==========================================================
    # 1. BUSCAR Y BLOQUEAR VENTA
    # ==========================================================

    try:

        venta = (
            Venta.objects
            .select_for_update()
            .get(
                id=venta_id
            )
        )

    except Venta.DoesNotExist:

        raise Exception(
            "La venta no existe."
        )

    # ==========================================================
    # 2. VALIDAR ESTADO DE VENTA
    # ==========================================================

    if venta.estado == "CANCELADA":

        raise Exception(
            "No se puede devolver una venta cancelada."
        )

    if venta.estado == "DEVUELTA":

        raise Exception(
            "La venta ya fue devuelta completamente."
        )

    # ==========================================================
    # 3. VALIDAR PLAZO DE DEVOLUCIÓN
    # ==========================================================

    if data["tipo"] == "NORMAL":

        empresa = Empresa.objects.first()

        if not empresa:

            raise Exception(
                "No existe configuración de empresa."
            )

        dias = empresa.dias_devolucion

        diferencia = (
            timezone.now()
            -
            venta.fecha
        ).days

        if diferencia > dias:

            raise Exception(
                "El periodo de devolución expiró."
            )

    # ==========================================================
    # 4. VALIDAR MÉTODO DE REEMBOLSO
    # ==========================================================

    metodo_pago_reembolso_id = data[
        "metodo_pago_reembolso_id"
    ]

    try:

        metodo_pago_reembolso = (
            MetodoPago.objects
            .get(
                id=metodo_pago_reembolso_id,
                activo=True
            )
        )

    except MetodoPago.DoesNotExist:

        raise Exception(
            "El método de reembolso no existe o está inactivo."
        )

    # ==========================================================
    # 5. CREAR CABECERA
    # ==========================================================

    devolucion = Devolucion.objects.create(

        venta=venta,

        usuario=usuario,

        metodo_pago_reembolso=(
            metodo_pago_reembolso
        ),

        tipo=data["tipo"],

        motivo=data["motivo"],

        estado="PENDIENTE"

    )

    # ==========================================================
    # 6. OBTENER SUBTOTAL BRUTO DE LA VENTA
    # ==========================================================

    subtotal_bruto_venta = (
        DetalleVenta.objects
        .filter(
            venta=venta
        )
        .aggregate(
            total=models.Sum("subtotal")
        )["total"]
        or Decimal("0.00")
    )

    subtotal_bruto_venta = (
        subtotal_bruto_venta
        .quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
    )

    if subtotal_bruto_venta <= 0:

        raise Exception(
            "La venta no tiene un subtotal válido."
        )

    # ==========================================================
    # 7. CALCULAR FACTOR REAL DE LA VENTA
    # ==========================================================

    factor_reembolso = (
        venta.subtotal
        /
        subtotal_bruto_venta
    )

    # ==========================================================
    # 8. CREAR DETALLES
    # ==========================================================

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

            raise Exception(
                "El producto no pertenece a la venta."
            )

        cantidad = item["cantidad"]

        # ------------------------------------------------------
        # VALIDAR CANTIDAD
        # ------------------------------------------------------

        if cantidad <= 0:

            raise Exception(
                "La cantidad debe ser mayor a cero."
            )

        # ------------------------------------------------------
        # CANTIDAD YA COMPROMETIDA EN DEVOLUCIONES
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # CANTIDAD YA COMPROMETIDA EN GARANTÍAS
        # ------------------------------------------------------

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
                total=models.Sum("cantidad")
            )["total"]
            or 0
        )

        # ------------------------------------------------------
        # CUPÓN ÚNICO DE UNIDADES
        # ------------------------------------------------------

        disponible = (
            detalle_venta.cantidad
            -
            cantidad_devuelta
            -
            cantidad_garantizada
        )

        if disponible < 0:

            disponible = 0

        if cantidad > disponible:

            raise Exception(
                "La cantidad solicitada para devolución "
                "supera las unidades disponibles. "
                f"Disponibles: {disponible}."
            )

        # ------------------------------------------------------
        # IMPORTE BRUTO DE LA LÍNEA
        # ------------------------------------------------------

        subtotal_bruto = (
            cantidad
            *
            detalle_venta.precio_unitario
        )

        subtotal_bruto = (
            subtotal_bruto
            .quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )
        )

        # ------------------------------------------------------
        # IMPORTE NETO REEMBOLSABLE
        # ------------------------------------------------------

        subtotal = (
            subtotal_bruto
            *
            factor_reembolso
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        # ------------------------------------------------------
        # CREAR DETALLE
        # ------------------------------------------------------

        DetalleDevolucion.objects.create(

            devolucion=devolucion,

            detalle_venta=detalle_venta,

            cantidad=cantidad,

            precio_original=(
                detalle_venta.precio_unitario
            ),

            subtotal=subtotal

        )

        total += subtotal

    # ==========================================================
    # 9. VALIDAR TOTAL NETO
    # ==========================================================

    total = (
        total
        .quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
    )

    if total <= 0:

        raise Exception(
            "El importe de la devolución "
            "debe ser mayor que cero."
        )

    # ==========================================================
    # 10. CALCULAR IVA PROPORCIONAL
    # ==========================================================

    if venta.subtotal > 0:

        iva_devolucion = (
            total
            *
            venta.iva
        ) / venta.subtotal

        iva_devolucion = (
            iva_devolucion
            .quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )
        )

    else:

        iva_devolucion = Decimal("0.00")

    # ==========================================================
    # 11. TOTAL FINAL
    # ==========================================================

    total_devuelto = (
        total
        +
        iva_devolucion
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    # ==========================================================
    # 12. NO PERMITIR REEMBOLSAR MÁS DE LO COBRADO
    # ==========================================================

    if total_devuelto > venta.total:

        total_devuelto = venta.total

    # ==========================================================
    # 13. GUARDAR TOTAL
    # ==========================================================

    devolucion.total_devuelto = (
        total_devuelto
    )

    devolucion.save(
        update_fields=[
            "total_devuelto"
        ]
    )

    # ==========================================================
    # BITÁCORA
    # ==========================================================

    registrar_bitacora(

        usuario=usuario,

        modulo="Devoluciones",

        accion="DEVOLUCION_CREADA",

        descripcion=(

            f"Devolución '{devolucion.id}' "
            f"creada para la venta "
            f"'{venta.folio}' por "
            f"{usuario.nombre} "
            f"{usuario.apellido}. "

            f"Tipo: {devolucion.tipo}. "

            f"Motivo: {devolucion.motivo}. "

            f"Total devuelto: "
            f"${devolucion.total_devuelto}. "

            f"Método de reembolso: "
            f"{metodo_pago_reembolso.nombre}. "

            f"Estado: PENDIENTE."

        )

    )

    return devolucion


# ==============================================================
# APROBAR DEVOLUCIÓN
# ==============================================================

@transaction.atomic
def aprobar_devolucion(
    devolucion_id,
    usuario
):

    # ==========================================================
    # 1. BUSCAR Y BLOQUEAR DEVOLUCIÓN
    # ==========================================================

    try:

        devolucion = (
            Devolucion.objects
            .select_for_update()
            .get(
                id=devolucion_id
            )
        )

    except Devolucion.DoesNotExist:

        raise Exception(
            "La devolución no existe."
        )

    # ==========================================================
    # 2. VALIDAR ESTADO
    # ==========================================================

    if devolucion.estado != "PENDIENTE":

        raise Exception(
            "Solo se pueden aprobar devoluciones pendientes."
        )

    # ==========================================================
    # 3. BUSCAR Y BLOQUEAR VENTA
    # ==========================================================

    try:

        venta = (
            Venta.objects
            .select_for_update()
            .get(
                id=devolucion.venta_id
            )
        )

    except Venta.DoesNotExist:

        raise Exception(
            "La venta asociada no existe."
        )

    # ==========================================================
    # 4. VALIDAR VENTA
    # ==========================================================

    if venta.estado == "CANCELADA":

        raise Exception(
            "No se puede aprobar una devolución "
            "de una venta cancelada."
        )

    if venta.estado == "DEVUELTA":

        raise Exception(
            "La venta ya fue devuelta completamente."
        )

    # ==========================================================
    # 5. VALIDAR MÉTODO DE REEMBOLSO
    # ==========================================================

    if not devolucion.metodo_pago_reembolso:

        raise Exception(
            "La devolución no tiene un método de reembolso."
        )

    metodo_pago = (
        devolucion.metodo_pago_reembolso
    )

    # ==========================================================
    # 6. OBTENER DETALLES
    # ==========================================================

    detalles = list(
        devolucion.detalles.select_related(
            "detalle_venta"
        )
    )

    if not detalles:

        raise Exception(
            "La devolución no tiene productos."
        )

    # ==========================================================
    # 7. VALIDAR NUEVAMENTE CANTIDADES
    # ==========================================================

    for detalle in detalles:

        detalle_venta = (
            detalle.detalle_venta
        )

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

        # ------------------------------------------------------
        # Otras devoluciones pendientes
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # Garantías comprometidas
        # ------------------------------------------------------

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
                total=models.Sum("cantidad")
            )["total"]
            or 0
        )

        disponible = (
            detalle_venta.cantidad
            -
            cantidad_aprobada
            -
            cantidad_pendiente
            -
            cantidad_garantizada
        )

        if disponible < 0:

            disponible = 0

        if detalle.cantidad > disponible:

            raise Exception(
                "La cantidad devuelta supera "
                "la cantidad disponible."
            )

    # ==========================================================
    # 8. BUSCAR CORTE ABIERTO DE LA MISMA CAJA
    #     SOLO PARA REEMBOLSO EN EFECTIVO
    # ==========================================================

    corte = None

    if metodo_pago.nombre == "EFECTIVO":

        if not venta.corte_caja:

            raise Exception(
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

            raise Exception(
                "No existe un corte de caja abierto "
                "para registrar el reembolso."
            )

    # ==========================================================
    # 9. REPONER STOCK
    # ==========================================================

    for detalle in detalles:

        detalle_venta = (
            detalle.detalle_venta
        )

        # ------------------------------------------------------
        # BLOQUEAR VARIANTE
        # ------------------------------------------------------

        variante = (
            Variante.objects
            .select_for_update()
            .get(
                id=detalle_venta.variante_id
            )
        )

        # ------------------------------------------------------
        # STOCK ANTERIOR
        # ------------------------------------------------------

        stock_anterior = (
            variante.stock
        )

        # ------------------------------------------------------
        # STOCK NUEVO
        # ------------------------------------------------------

        stock_nuevo = (
            stock_anterior
            +
            detalle.cantidad
        )
        
        stock_defectuoso_anterior = (
            variante.stock_defectuoso
        )

        stock_defectuoso_nuevo = (
            stock_defectuoso_anterior
        )


        # ------------------------------------------------------
        # REGISTRAR MOVIMIENTO
        # ------------------------------------------------------

        MovimientoInventario.objects.create(

            variante=variante,

            tipo="DEVOLUCION",

            stock_anterior=stock_anterior,

            cantidad=detalle.cantidad,

            stock_nuevo=stock_nuevo,
            
            stock_defectuoso_anterior=(
            
            stock_defectuoso_anterior
            
            ),

            stock_defectuoso_nuevo=(
                stock_defectuoso_nuevo
            ),
    

            observaciones=(
                f"Devolución {devolucion.id}"
            ),

            usuario=usuario

        )

        # ------------------------------------------------------
        # ACTUALIZAR STOCK
        # ------------------------------------------------------

        variante.stock = stock_nuevo

        variante.save(
            update_fields=[
                "stock",
                "fecha_actualizacion"
            ]
        )

    # ==========================================================
    # 10. REGISTRAR REEMBOLSO EN CAJA
    #     SOLO PARA EFECTIVO
    # ==========================================================

    if metodo_pago.nombre == "EFECTIVO":

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

            usuario=usuario

        )

    # ==========================================================
    # 11. APROBAR DEVOLUCIÓN
    # ==========================================================

    devolucion.estado = "APROBADA"

    devolucion.save(
        update_fields=[
            "estado"
        ]
    )

    # ==========================================================
    # BITÁCORA
    # ==========================================================

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
            f"${devolucion.total_devuelto}. "

            f"Método de reembolso: "
            f"{metodo_pago.nombre}."

        )

    )

    # ==========================================================
    # 12. DETERMINAR SI TODA LA VENTA FUE DEVUELTA
    # ==========================================================

    venta_completamente_devuelta = True

    detalles_venta = (
        venta.detalles.all()
    )

    for detalle_venta in detalles_venta:

        cantidad_devuelta = (
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

        if cantidad_devuelta < detalle_venta.cantidad:

            venta_completamente_devuelta = False

            break

    # ==========================================================
    # 13. ACTUALIZAR ESTADO DE VENTA
    # ==========================================================

    if venta_completamente_devuelta:

        venta.estado = "DEVUELTA"

        venta.save(
            update_fields=[
                "estado"
            ]
        )

    return devolucion


# ==============================================================
# RECHAZAR DEVOLUCIÓN
# ==============================================================

@transaction.atomic
def cambiar_estado_devolucion(
    devolucion_id,
    nuevo_estado,
    usuario
):

    # ==========================================================
    # BUSCAR Y BLOQUEAR
    # ==========================================================

    try:

        devolucion = (
            Devolucion.objects
            .select_for_update()
            .get(
                id=devolucion_id
            )
        )

    except Devolucion.DoesNotExist:

        raise Exception(
            "La devolución no existe."
        )

    # ==========================================================
    # VALIDAR ESTADO ACTUAL
    # ==========================================================

    if devolucion.estado != "PENDIENTE":

        raise Exception(
            "Solo se pueden modificar "
            "devoluciones pendientes."
        )

    # ==========================================================
    # SOLO RECHAZAR
    # ==========================================================

    if nuevo_estado != "RECHAZADA":

        raise Exception(
            "Para aprobar una devolución "
            "debe utilizarse el proceso de aprobación."
        )

    # ==========================================================
    # CAMBIAR ESTADO
    # ==========================================================

    devolucion.estado = "RECHAZADA"

    devolucion.save(
        update_fields=[
            "estado"
        ]
    )

    # ==========================================================
    # BITÁCORA
    # ==========================================================

    registrar_bitacora(

        usuario=usuario,

        modulo="Devoluciones",

        accion="DEVOLUCION_RECHAZADA",

        descripcion=(

            f"Devolución '{devolucion.id}' "
            f"rechazada por "
            f"{usuario.nombre} "
            f"{usuario.apellido}. "

            f"Venta: "
            f"'{devolucion.venta.folio}'. "

            f"Motivo registrado: "
            f"{devolucion.motivo}."

        )

    )

    return devolucion