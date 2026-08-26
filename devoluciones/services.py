from decimal import Decimal, ROUND_HALF_UP

from django.db import models, transaction
from django.utils import timezone

from ventas.models import Venta
from empresa.models import Empresa
from detalle_venta.models import DetalleVenta

from inventario.models import MovimientoInventario
from metodos_pago.models import MetodoPago

from corte_caja.models import MovimientoCaja, CorteCaja

from .models import (
    Devolucion,
    DetalleDevolucion
)

from variantes.models import Variante

from bitacora.services import registrar_bitacora


@transaction.atomic
def crear_devolucion(
    data,
    usuario
):

    venta_id = data["venta_id"]

    productos = data["productos"]


    # 1. Buscar venta

    try:

        venta = Venta.objects.get(
            id=venta_id
        )

    except Venta.DoesNotExist:

        raise Exception(
            "La venta no existe."
        )


    # 2. Validar estado de venta

    if venta.estado == "CANCELADA":

        raise Exception(
            "No se puede devolver una venta cancelada."
        )


    # 3. Validar plazo de devolución

    if data["tipo"] == "NORMAL":

        empresa = Empresa.objects.first()

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


    total = Decimal("0.00")


    # 4. Buscar método de reembolso

    metodo_pago_reembolso_id = data[
        "metodo_pago_reembolso_id"
    ]

    try:

        metodo_pago_reembolso = MetodoPago.objects.get(
            id=metodo_pago_reembolso_id,
            activo=True
        )

    except MetodoPago.DoesNotExist:

        raise Exception(
            "El método de reembolso no existe o está inactivo."
        )


    # 5. Crear cabecera

    devolucion = Devolucion.objects.create(

        venta=venta,

        usuario=usuario,

        metodo_pago_reembolso=metodo_pago_reembolso,

        tipo=data["tipo"],

        motivo=data["motivo"],

        estado="PENDIENTE"

    )


    # 6. Crear detalles

    for item in productos:

        try:

            detalle_venta = DetalleVenta.objects.get(

                id=item["detalle_venta_id"],

                venta=venta

            )

        except DetalleVenta.DoesNotExist:

            raise Exception(
                "El producto no pertenece a la venta."
            )


        cantidad = item["cantidad"]


        # Validar cantidad ya devuelta

        cantidad_devuelta = (
            detalle_venta
            .devoluciones
            .aggregate(
                total=models.Sum("cantidad")
            )
            ["total"]
            or 0
        )


        disponible = (
            detalle_venta.cantidad
            -
            cantidad_devuelta
        )


        if cantidad > disponible:

            raise Exception(
                "La cantidad devuelta supera la vendida."
            )


        # Calcular subtotal de la devolución

        subtotal = (
            cantidad *
            detalle_venta.precio_unitario
        )


        DetalleDevolucion.objects.create(

            devolucion=devolucion,

            detalle_venta=detalle_venta,

            cantidad=cantidad,

            precio_original=detalle_venta.precio_unitario,

            subtotal=subtotal

        )


        total += subtotal


    # 7. Calcular IVA proporcional de la venta

    if venta.subtotal > 0:

        iva_devolucion = (
            total *
            venta.iva
        ) / venta.subtotal

        iva_devolucion = iva_devolucion.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    else:

        iva_devolucion = Decimal("0.00")


    # 8. Calcular total final de devolución

    total_devuelto = (
        total +
        iva_devolucion
    )


    # 9. Guardar total

    devolucion.total_devuelto = total_devuelto

    devolucion.save()


    # ==========================================
    # BITÁCORA
    # ==========================================

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


@transaction.atomic
def aprobar_devolucion(
    devolucion_id,
    usuario
):

    # 1. Buscar y bloquear la devolución

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


    # 2. Validar estado

    if devolucion.estado != "PENDIENTE":

        raise Exception(
            "Solo se pueden aprobar devoluciones pendientes."
        )


    # 3. Buscar y bloquear la venta

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


    # 4. Validar venta

    if venta.estado == "CANCELADA":

        raise Exception(
            "No se puede aprobar una devolución "
            "de una venta cancelada."
        )


    # 5. Validar método de reembolso

    if not devolucion.metodo_pago_reembolso:

        raise Exception(
            "La devolución no tiene un método de reembolso."
        )


    metodo_pago = devolucion.metodo_pago_reembolso


    # 6. Obtener detalles

    detalles = list(
        devolucion.detalles.select_related(
            "detalle_venta"
        )
    )


    if not detalles:

        raise Exception(
            "La devolución no tiene productos."
        )


    # 7. Validar nuevamente cantidades

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

        disponible = (
            detalle_venta.cantidad
            - cantidad_aprobada
        )

        if detalle.cantidad > disponible:

            raise Exception(
                "La cantidad devuelta supera "
                "la cantidad disponible."
            )


    # 8. Buscar corte abierto de la MISMA CAJA
    #    únicamente si el reembolso es efectivo

    corte = None

    if metodo_pago.nombre == "EFECTIVO":

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


    # 9. Reponer stock

    for detalle in detalles:

        detalle_venta = detalle.detalle_venta

        # Bloquear variante

        variante = (
            Variante.objects
            .select_for_update()
            .get(
                id=detalle_venta.variante_id
            )
        )

        # Reponer stock

        variante.stock += detalle.cantidad

        variante.save(
            update_fields=[
                "stock"
            ]
        )


        # Registrar movimiento de inventario

        MovimientoInventario.objects.create(

            variante=variante,

            tipo="DEVOLUCION",

            cantidad=detalle.cantidad,

            observaciones=(
                f"Devolución {devolucion.id}"
            ),

            usuario=usuario
        )


    # 10. Registrar reembolso en caja
    #     únicamente para efectivo

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


    # 11. Aprobar devolución

    devolucion.estado = "APROBADA"

    devolucion.save(
        update_fields=[
            "estado"
        ]
    )


    # ==========================================
    # BITÁCORA
    # ==========================================

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


    # 12. Determinar si toda la venta fue devuelta

    venta_completamente_devuelta = True

    detalles_venta = venta.detalles.all()

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


    # 13. Actualizar estado de venta

    if venta_completamente_devuelta:

        venta.estado = "DEVUELTA"

        venta.save(
            update_fields=[
                "estado"
            ]
        )


    return devolucion


@transaction.atomic
def cambiar_estado_devolucion(
    devolucion_id,
    nuevo_estado,
    usuario
):

    try:

        devolucion = Devolucion.objects.get(
            id=devolucion_id
        )

    except Devolucion.DoesNotExist:

        raise Exception(
            "La devolución no existe."
        )


    if devolucion.estado != "PENDIENTE":

        raise Exception(
            "Solo se pueden modificar "
            "devoluciones pendientes."
        )


    if nuevo_estado != "RECHAZADA":

        raise Exception(
            "Para aprobar una devolución "
            "debe utilizarse el proceso de aprobación."
        )


    devolucion.estado = "RECHAZADA"

    devolucion.save(
        update_fields=[
            "estado"
        ]
    )


    # ==========================================
    # BITÁCORA
    # ==========================================

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

        )

    )


    return devolucion