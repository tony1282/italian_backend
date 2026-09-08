from decimal import Decimal, InvalidOperation

from django.db import transaction, connection
from django.db.models import Max

from .models import Venta

from detalle_venta.models import DetalleVenta
from variantes.models import Variante
from metodos_pago.models import MetodoPago
from empresa.models import Empresa
from cajas.models import Caja
from corte_caja.models import CorteCaja
from inventario.models import MovimientoInventario

from config.exceptions import BusinessException
from bitacora.services import registrar_bitacora


# ==============================================================
# VALIDACIONES DE ENTRADA
# ==============================================================

def validar_descuento(valor):
    try:
        descuento = Decimal(str(valor or "0"))
    except (InvalidOperation, TypeError, ValueError):
        raise BusinessException("El descuento debe ser un valor numérico válido.")

    if not descuento.is_finite():
        raise BusinessException("El descuento debe ser un valor válido.")

    descuento = descuento.quantize(Decimal("0.01"))

    if descuento < 0:
        raise BusinessException("El descuento no puede ser negativo.")

    return descuento


def validar_item_producto(item):
    if not isinstance(item, dict):
        raise BusinessException("Cada producto debe tener un formato válido.")

    variante_id = item.get("variante_id")
    if not variante_id:
        raise BusinessException("Cada producto debe indicar su variante.")

    cantidad_raw = item.get("cantidad")

    # --------------------------------------------------------
    # Rechazar booleanos explícitamente. bool es subclase de
    # int en Python, así que int(True) == 1 e int(False) == 0
    # se colarían como cantidades válidas si no se valida antes
    # (mismo criterio ya aplicado en inventario/services.py).
    # --------------------------------------------------------
    if isinstance(cantidad_raw, bool):
        raise BusinessException("La cantidad debe ser un número entero.")

    # --------------------------------------------------------
    # Rechazar floats no enteros (1.5, -1.5, etc). int(1.5) los
    # truncaría a 1 sin lanzar ningún error.
    # --------------------------------------------------------
    if isinstance(cantidad_raw, float) and not cantidad_raw.is_integer():
        raise BusinessException("La cantidad debe ser un número entero.")

    try:
        cantidad = int(cantidad_raw)
    except (TypeError, ValueError):
        raise BusinessException("La cantidad debe ser un número entero.")

    if cantidad <= 0:
        raise BusinessException("La cantidad debe ser mayor que cero.")

    return variante_id, cantidad


# ==============================================================
# OBTENER RECURSOS
# ==============================================================

def obtener_caja(caja_id):
    try:
        return Caja.objects.get(id=caja_id)
    except (Caja.DoesNotExist, ValueError, TypeError):
        raise BusinessException("La caja no existe.")


def obtener_metodo_pago(metodo_pago_id):
    try:
        return MetodoPago.objects.get(id=metodo_pago_id, activo=True)
    except (MetodoPago.DoesNotExist, ValueError, TypeError):
        raise BusinessException("El método de pago no existe o está inactivo.")


def obtener_iva():
    empresa = Empresa.objects.first()
    if not empresa:
        raise BusinessException("No hay configuración de empresa.")

    iva = Decimal(str(empresa.iva))
    if not iva.is_finite():
        raise BusinessException("El IVA configurado no es válido.")

    return iva


def obtener_corte_abierto(caja):
    try:
        return (
            CorteCaja.objects
            .select_for_update()
            .select_related("caja")
            .get(caja=caja, fecha_fin__isnull=True)
        )
    except CorteCaja.DoesNotExist:
        raise BusinessException("La caja no tiene un corte abierto.")


def generar_folio():
    ultima = Venta.objects.aggregate(Max("folio"))["folio__max"]
    if ultima:
        try:
            numero = int(ultima.split("-")[1]) + 1
        except (IndexError, ValueError):
            raise BusinessException("No se pudo generar el folio de la venta.")
    else:
        numero = 1
    return f"V-{numero:07d}"


# ==============================================================
# PROCESAR UN ITEM DE PRODUCTO
# ==============================================================

def procesar_item_venta(item, venta, folio, usuario):
    variante_id, cantidad = validar_item_producto(item)

    try:
        variante = (
            Variante.objects
            .select_for_update()
            .select_related("producto")
            .get(id=variante_id)
        )
    except (Variante.DoesNotExist, ValueError, TypeError):
        raise BusinessException("La variante no existe.")

    if not variante.activo:
        raise BusinessException("La variante está inactiva.")

    if not variante.producto.activo:
        raise BusinessException("El producto está inactivo.")

    precio_unitario = Decimal(str(variante.precio_menudeo))
    if not precio_unitario.is_finite():
        raise BusinessException("El precio del producto no es válido.")

    if precio_unitario < 0:
        raise BusinessException("El precio del producto no puede ser negativo.")

    precio_unitario = precio_unitario.quantize(Decimal("0.01"))

    stock_anterior = variante.stock
    stock_defectuoso_anterior = variante.stock_defectuoso

    if stock_anterior < cantidad:
        raise BusinessException(
            "Stock insuficiente.",
            data={
                "variante_id": str(variante.id),
                "producto": variante.producto.nombre,
                "variante": variante.nombre,
                "stock_actual": stock_anterior,
                "cantidad_solicitada": cantidad,
            }
        )

    stock_nuevo = stock_anterior - cantidad
    subtotal_linea = (precio_unitario * cantidad).quantize(Decimal("0.01"))

    DetalleVenta.objects.create(
        venta=venta,
        variante=variante,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        descuento=Decimal("0.00"),
        subtotal=subtotal_linea,
    )

    MovimientoInventario.objects.create(
        variante=variante,
        tipo="SALIDA",
        stock_anterior=stock_anterior,
        cantidad=cantidad,
        stock_nuevo=stock_nuevo,
        stock_defectuoso_anterior=stock_defectuoso_anterior,
        stock_defectuoso_nuevo=stock_defectuoso_anterior,
        observaciones=f"Venta {folio}",
        usuario=usuario,
    )

    variante.stock = stock_nuevo
    variante.save(update_fields=["stock", "fecha_actualizacion"])

    return subtotal_linea


# ==============================================================
# CREAR VENTA
# ==============================================================

@transaction.atomic
def crear_venta(data, usuario):
    caja_id = data.get("caja_id")
    metodo_pago_id = data.get("metodo_pago_id")
    productos = data.get("productos", [])

    if not caja_id:
        raise BusinessException("Debe indicar una caja.")

    if not metodo_pago_id:
        raise BusinessException("Debe indicar un método de pago.")

    if not isinstance(productos, list) or not productos:
        raise BusinessException("Debe agregar al menos un producto.")

    descuento = validar_descuento(data.get("descuento", "0"))

    caja = obtener_caja(caja_id)

    if not caja.activa:
        raise BusinessException("La caja está inactiva.")

    if caja.estado != "ABIERTA":
        raise BusinessException("La caja está cerrada.")

    metodo_pago = obtener_metodo_pago(metodo_pago_id)
    iva_porcentaje = obtener_iva()

    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext('ventas_folio'))")

    corte = obtener_corte_abierto(caja)

    if usuario.rol not in (0, 1) and corte.usuario_id != usuario.id:
        raise BusinessException("Esta caja está siendo utilizada por otro empleado.")

    folio = generar_folio()

    venta = Venta.objects.create(
        folio=folio,
        usuario=usuario,
        corte_caja=corte,
        metodo_pago=metodo_pago,
        subtotal=Decimal("0.00"),
        descuento=descuento,
        iva=Decimal("0.00"),
        total=Decimal("0.00"),
    )

    subtotal = Decimal("0.00")
    for item in productos:
        subtotal += procesar_item_venta(item, venta, folio, usuario)

    if subtotal <= 0:
        raise BusinessException("El subtotal de la venta debe ser mayor que cero.")

    if descuento > subtotal:
        raise BusinessException("El descuento no puede ser mayor al subtotal.")

    subtotal_final = (subtotal - descuento).quantize(Decimal("0.01"))
    iva = (subtotal_final * (iva_porcentaje / Decimal("100"))).quantize(Decimal("0.01"))
    total = (subtotal_final + iva).quantize(Decimal("0.01"))

    venta.subtotal = subtotal_final
    venta.descuento = descuento
    venta.iva = iva
    venta.total = total
    venta.save(update_fields=["subtotal", "descuento", "iva", "total"])

    registrar_bitacora(
        usuario=usuario,
        modulo="Ventas",
        accion="REGISTRAR_VENTA",
        descripcion=(
            f"Venta folio {venta.folio} registrada correctamente por "
            f"{usuario.nombre} {usuario.apellido}. Total: ${venta.total:.2f}"
        ),
    )

    return venta


# ==============================================================
# CANCELAR VENTA
# ==============================================================

@transaction.atomic
def cancelar_venta(venta_id, usuario):
    try:
        venta = Venta.objects.select_for_update().get(id=venta_id)
    except (Venta.DoesNotExist, ValueError, TypeError):
        raise BusinessException("La venta no existe.")

    if usuario.rol not in (0, 1) and venta.usuario_id != usuario.id:
        raise BusinessException("Solo puedes cancelar tus propias ventas.")

    if venta.estado == "CANCELADA":
        raise BusinessException("La venta ya está cancelada.")

    if venta.estado == "DEVUELTA":
        raise BusinessException("No se puede cancelar una venta que ya fue devuelta completamente.")

    from devoluciones.models import Devolucion
    if Devolucion.objects.filter(venta=venta, estado__in=["PENDIENTE", "APROBADA"]).exists():
        raise BusinessException(
            "No se puede cancelar la venta porque tiene una devolución pendiente o aprobada."
        )

    for detalle in venta.detalles.select_related("variante").all():
        variante = Variante.objects.select_for_update().get(id=detalle.variante_id)
        stock_anterior = variante.stock
        stock_nuevo = stock_anterior + detalle.cantidad
        stock_defectuoso_anterior = variante.stock_defectuoso

        MovimientoInventario.objects.create(
            variante=variante,
            tipo="ENTRADA",
            stock_anterior=stock_anterior,
            cantidad=detalle.cantidad,
            stock_nuevo=stock_nuevo,
            stock_defectuoso_anterior=stock_defectuoso_anterior,
            stock_defectuoso_nuevo=stock_defectuoso_anterior,
            observaciones=f"Cancelación {venta.folio}",
            usuario=usuario,
        )

        variante.stock = stock_nuevo
        variante.save(update_fields=["stock", "fecha_actualizacion"])

    venta.estado = "CANCELADA"
    venta.save(update_fields=["estado"])

    registrar_bitacora(
        usuario=usuario,
        modulo="Ventas",
        accion="CANCELAR_VENTA",
        descripcion=(
            f"Venta folio {venta.folio} cancelada correctamente por "
            f"{usuario.nombre} {usuario.apellido}. Se restauró el stock de los productos."
        ),
    )

    return venta