from empresa.models import Empresa
from ventas.models import Venta

from config.exceptions import BusinessException


def generar_ticket(venta_id):

    # ------------------------------------------------------
    # VENTA
    # --------------------------------------------------
    # Se hace una sola consulta (con sus relaciones ya
    # cargadas) en vez de verificar existencia por separado
    # en la vista y luego volver a consultar aquí.
    # Venta.DoesNotExist se deja propagar tal cual para que
    # la vista lo traduzca a un 404, igual que el resto del
    # proyecto (ventas/corte_caja lo manejan así).
    # ------------------------------------------------------

    venta = (
        Venta.objects
        .select_related("usuario", "metodo_pago")
        .prefetch_related("detalles__variante__producto")
        .get(id=venta_id)
    )

    # ------------------------------------------------------
    # EMPRESA
    # --------------------------------------------------
    # Sin configuración de empresa no se puede armar el
    # encabezado del ticket. Mismo guard que ya existe en
    # ventas/services.py::obtener_iva().
    # ------------------------------------------------------

    empresa = Empresa.objects.first()

    if not empresa:
        raise BusinessException("No hay configuración de empresa.")

    return {
        "empresa": {
            "nombre": empresa.nombre,
            "telefono": empresa.telefono,
            "direccion": empresa.direccion,
            "rfc": empresa.rfc,
            "mensaje_ticket": empresa.mensaje_ticket,
        },
        "venta": {
            "folio": venta.folio,
            "fecha": venta.fecha,
            "metodo_pago": venta.metodo_pago.nombre,
        },
        "usuario": {
            "nombre": venta.usuario.nombre,
        },
        "productos": [
            {
                "producto": d.variante.producto.nombre,
                "variante": d.variante.nombre,
                "cantidad": d.cantidad,
                "precio": d.precio_unitario,
                "subtotal": d.subtotal,
            }
            for d in venta.detalles.all()
        ],
        "totales": {
            "subtotal": venta.subtotal,
            "descuento": venta.descuento,
            "iva": venta.iva,
            "total": venta.total,
        },
    }