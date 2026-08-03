from empresa.models import Empresa
from ventas.models import Venta


def generar_ticket(venta_id):

    empresa = Empresa.objects.first()


    venta = Venta.objects.select_related(
        "usuario",
        "metodo_pago",
    ).prefetch_related(
        "detalles__variante__producto"
    ).get(
        id=venta_id
    )


    productos = []


    for detalle in venta.detalles.all():

        productos.append(
            {
                "producto": detalle.variante.producto.nombre,

                "variante": detalle.variante.nombre,

                "cantidad": detalle.cantidad,

                "precio": detalle.precio_unitario,

                "subtotal": detalle.subtotal,
            }
        )


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

            "nombre": venta.usuario.nombre

        },


        "productos": productos,


        "totales": {

            "subtotal": venta.subtotal,

            "iva": venta.iva,

            "total": venta.total

        }

    }