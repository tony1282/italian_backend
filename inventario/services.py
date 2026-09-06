import uuid

from django.db import transaction

from variantes.models import Variante
from bitacora.services import registrar_bitacora
from config.exceptions import BusinessException

from .models import MovimientoInventario


# ==============================================================
# VALIDACIONES COMUNES
# ==============================================================

def validar_uuid(valor):
    try:
        uuid.UUID(str(valor))
    except (TypeError, ValueError, AttributeError):
        raise BusinessException("El identificador de la variante no es válido.")


def validar_cantidad(valor):
    # ----------------------------------------------------------
    # Rechazar booleanos explícitamente. bool es subclase de int
    # en Python, así que int(True) == 1 e int(False) == 0 se
    # colarían como cantidades válidas si no se valida antes.
    # ----------------------------------------------------------
    if isinstance(valor, bool):
        raise BusinessException("La cantidad debe ser un número entero.")

    # ----------------------------------------------------------
    # Rechazar floats no enteros (1.5, -1.5, etc). int(1.5) los
    # truncaría a 1 sin lanzar ningún error.
    # ----------------------------------------------------------
    if isinstance(valor, float) and not valor.is_integer():
        raise BusinessException("La cantidad debe ser un número entero.")

    try:
        cantidad = int(valor)
    except (TypeError, ValueError):
        raise BusinessException("La cantidad debe ser un número entero.")

    if cantidad <= 0:
        raise BusinessException("La cantidad debe ser mayor a cero.")

    return cantidad


def validar_stock_nuevo(valor):
    # ----------------------------------------------------------
    # Misma protección contra booleanos y decimales que
    # validar_cantidad(), pero aquí 0 es un valor válido y no
    # se exige "> 0", por lo que no se reutiliza esa función.
    # ----------------------------------------------------------
    if isinstance(valor, bool):
        raise BusinessException("El stock nuevo debe ser un número entero.")

    if isinstance(valor, float) and not valor.is_integer():
        raise BusinessException("El stock nuevo debe ser un número entero.")

    try:
        stock_nuevo = int(valor)
    except (TypeError, ValueError):
        raise BusinessException("El stock nuevo debe ser un número entero.")

    if stock_nuevo < 0:
        raise BusinessException("El stock no puede ser negativo.")

    return stock_nuevo


def obtener_variante_bloqueada(variante_id):
    try:
        return Variante.objects.select_for_update().get(id=variante_id)
    except Variante.DoesNotExist:
        raise BusinessException("La variante no existe.")


def _crear_movimiento(variante, tipo, stock_anterior, cantidad, stock_nuevo,
                      stock_defectuoso_anterior, stock_defectuoso_nuevo,
                      observaciones, usuario):
    return MovimientoInventario.objects.create(
        variante=variante,
        tipo=tipo,
        stock_anterior=stock_anterior,
        cantidad=cantidad,
        stock_nuevo=stock_nuevo,
        stock_defectuoso_anterior=stock_defectuoso_anterior,
        stock_defectuoso_nuevo=stock_defectuoso_nuevo,
        observaciones=observaciones,
        usuario=usuario,
    )


# ==============================================================
# ENTRADA
# ==============================================================

@transaction.atomic
def registrar_entrada(variante_id, cantidad, observaciones, usuario):
    validar_uuid(variante_id)
    cantidad = validar_cantidad(cantidad)

    variante = obtener_variante_bloqueada(variante_id)

    stock_anterior = variante.stock
    stock_nuevo = stock_anterior + cantidad

    # La entrada de stock vendible no modifica el stock
    # defectuoso; se deja explícito con su propia variable.
    stock_defectuoso_anterior = variante.stock_defectuoso
    stock_defectuoso_nuevo = stock_defectuoso_anterior

    movimiento = _crear_movimiento(
        variante=variante,
        tipo="ENTRADA",
        stock_anterior=stock_anterior,
        cantidad=cantidad,
        stock_nuevo=stock_nuevo,
        stock_defectuoso_anterior=stock_defectuoso_anterior,
        stock_defectuoso_nuevo=stock_defectuoso_nuevo,
        observaciones=observaciones,
        usuario=usuario,
    )

    variante.stock = stock_nuevo
    variante.save(update_fields=["stock", "fecha_actualizacion"])

    registrar_bitacora(
        usuario=usuario,
        modulo="Inventario",
        accion="ENTRADA_INVENTARIO",
        descripcion=(
            f"Entrada de inventario registrada para la variante '{variante.nombre}' "
            f"por {usuario.nombre} {usuario.apellido}. "
            f"Stock anterior: {stock_anterior}. Cantidad ingresada: {cantidad}. "
            f"Stock nuevo: {stock_nuevo}."
        ),
    )

    return movimiento, stock_anterior, stock_nuevo, stock_defectuoso_anterior, stock_defectuoso_nuevo


# ==============================================================
# SALIDA
# ==============================================================

@transaction.atomic
def registrar_salida(variante_id, cantidad, observaciones, usuario):
    validar_uuid(variante_id)
    cantidad = validar_cantidad(cantidad)

    variante = obtener_variante_bloqueada(variante_id)

    stock_anterior = variante.stock

    if stock_anterior < cantidad:
        raise BusinessException(
            "Stock insuficiente.",
            data={"stock_actual": stock_anterior, "cantidad_solicitada": cantidad},
        )

    stock_nuevo = stock_anterior - cantidad

    # La salida de stock vendible no modifica el stock
    # defectuoso; se deja explícito con su propia variable.
    stock_defectuoso_anterior = variante.stock_defectuoso
    stock_defectuoso_nuevo = stock_defectuoso_anterior

    movimiento = _crear_movimiento(
        variante=variante,
        tipo="SALIDA",
        stock_anterior=stock_anterior,
        cantidad=cantidad,
        stock_nuevo=stock_nuevo,
        stock_defectuoso_anterior=stock_defectuoso_anterior,
        stock_defectuoso_nuevo=stock_defectuoso_nuevo,
        observaciones=observaciones,
        usuario=usuario,
    )

    variante.stock = stock_nuevo
    variante.save(update_fields=["stock", "fecha_actualizacion"])

    registrar_bitacora(
        usuario=usuario,
        modulo="Inventario",
        accion="SALIDA_INVENTARIO",
        descripcion=(
            f"Salida de inventario registrada para la variante '{variante.nombre}' "
            f"por {usuario.nombre} {usuario.apellido}. "
            f"Stock anterior: {stock_anterior}. Cantidad retirada: {cantidad}. "
            f"Stock nuevo: {stock_nuevo}."
        ),
    )

    return movimiento, stock_anterior, stock_nuevo, stock_defectuoso_anterior, stock_defectuoso_nuevo


# ==============================================================
# AJUSTE
# ==============================================================

@transaction.atomic
def registrar_ajuste(variante_id, stock_nuevo_solicitado, observaciones, usuario):
    validar_uuid(variante_id)
    stock_nuevo_solicitado = validar_stock_nuevo(stock_nuevo_solicitado)

    variante = obtener_variante_bloqueada(variante_id)

    stock_anterior = variante.stock
    diferencia = stock_nuevo_solicitado - stock_anterior

    if diferencia == 0:
        raise BusinessException("El stock nuevo es igual al stock actual. No hay nada que ajustar.")

    cantidad = abs(diferencia)
    tipo_ajuste = "AUMENTO" if diferencia > 0 else "DISMINUCIÓN"

    # El ajuste de stock vendible no modifica el stock
    # defectuoso; se deja explícito con su propia variable.
    stock_defectuoso_anterior = variante.stock_defectuoso
    stock_defectuoso_nuevo = stock_defectuoso_anterior

    observacion_final = (
        f"{tipo_ajuste} de stock. {observaciones}" if observaciones else f"{tipo_ajuste} de stock."
    )

    movimiento = _crear_movimiento(
        variante=variante,
        tipo="AJUSTE",
        stock_anterior=stock_anterior,
        cantidad=cantidad,
        stock_nuevo=stock_nuevo_solicitado,
        stock_defectuoso_anterior=stock_defectuoso_anterior,
        stock_defectuoso_nuevo=stock_defectuoso_nuevo,
        observaciones=observacion_final,
        usuario=usuario,
    )

    variante.stock = stock_nuevo_solicitado
    variante.save(update_fields=["stock", "fecha_actualizacion"])

    registrar_bitacora(
        usuario=usuario,
        modulo="Inventario",
        accion="AJUSTE_INVENTARIO",
        descripcion=(
            f"Ajuste de inventario realizado para la variante '{variante.nombre}' "
            f"por {usuario.nombre} {usuario.apellido}. "
            f"Stock anterior: {stock_anterior}. Cantidad ajustada: {cantidad}. "
            f"Stock nuevo: {stock_nuevo_solicitado}. Tipo de ajuste: {tipo_ajuste}."
        ),
    )

    return (
        movimiento,
        stock_anterior,
        stock_nuevo_solicitado,
        stock_defectuoso_anterior,
        stock_defectuoso_nuevo,
        tipo_ajuste,
    )