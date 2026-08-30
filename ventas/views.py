from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Max, Sum

from rest_framework import (
    viewsets,
    status
)

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from rest_framework.decorators import action


from .models import Venta
from .serializers import VentaSerializer

from detalle_venta.models import DetalleVenta

from variantes.models import Variante
from metodos_pago.models import MetodoPago
from empresa.models import Empresa
from cajas.models import Caja
from corte_caja.models import CorteCaja
from inventario.models import MovimientoInventario

from devoluciones.models import Devolucion

from bitacora.services import registrar_bitacora


class VentaViewSet(
    viewsets.ModelViewSet
):

    queryset = Venta.objects.all()

    serializer_class = VentaSerializer

    # ==========================================================
    # MÉTODOS HTTP PERMITIDOS
    # ==========================================================

    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    # ==========================================================
    # PERMISOS
    # ==========================================================

    def get_permissions(self):

        return [
            IsAuthenticated()
        ]

    # ==========================================================
    # CREAR VENTA
    # ==========================================================

    def create(
        self,
        request,
        *args,
        **kwargs
    ):

        # ------------------------------------------------------
        # USUARIO ACTIVO
        # ------------------------------------------------------

        if not request.user.activo:

            return Response(
                {
                    "success": False,
                    "message": "El usuario está inactivo.",
                    "data": None
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # ------------------------------------------------------
        # DATOS
        # ------------------------------------------------------

        caja_id = request.data.get(
            "caja_id"
        )

        metodo_pago_id = request.data.get(
            "metodo_pago_id"
        )

        productos = request.data.get(
            "productos",
            []
        )

        # ======================================================
        # VALIDAR CAJA_ID
        # ======================================================

        if not caja_id:

            return Response(
                {
                    "success": False,
                    "message": "Debe indicar una caja.",
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ======================================================
        # VALIDAR METODO_PAGO_ID
        # ======================================================

        if not metodo_pago_id:

            return Response(
                {
                    "success": False,
                    "message": "Debe indicar un método de pago.",
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ======================================================
        # DESCUENTO
        # ======================================================

        try:

            descuento = Decimal(
                str(
                    request.data.get(
                        "descuento",
                        "0"
                    )
                )
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El descuento debe ser "
                        "un valor numérico válido."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not descuento.is_finite():

            return Response(
                {
                    "success": False,
                    "message": "El descuento debe ser un valor válido.",
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        descuento = descuento.quantize(
            Decimal("0.01")
        )

        if descuento < 0:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El descuento no puede ser negativo."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ======================================================
        # PRODUCTOS
        # ======================================================

        if not isinstance(
            productos,
            list
        ) or not productos:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Debe agregar al menos un producto."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ======================================================
        # CAJA
        # ======================================================

        try:

            caja = Caja.objects.get(
                id=caja_id
            )

        except (
            Caja.DoesNotExist,
            ValueError,
            TypeError
        ):

            return Response(
                {
                    "success": False,
                    "message": "La caja no existe.",
                    "data": None
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # ======================================================
        # VALIDAR CAJA ACTIVA
        # ======================================================

        if not caja.activa:

            return Response(
                {
                    "success": False,
                    "message": "La caja está inactiva.",
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ======================================================
        # VALIDAR CAJA ABIERTA
        # ======================================================

        if caja.estado != "ABIERTA":

            return Response(
                {
                    "success": False,
                    "message": "La caja está cerrada.",
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ======================================================
        # CORTE ABIERTO
        # ======================================================

        try:

            corte = (
                CorteCaja.objects
                .select_related(
                    "caja"
                )
                .get(
                    caja=caja,
                    fecha_fin__isnull=True
                )
            )

        except CorteCaja.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": (
                        "La caja no tiene un corte abierto."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ======================================================
        # MÉTODO DE PAGO
        # ======================================================

        try:

            metodo_pago = MetodoPago.objects.get(
                id=metodo_pago_id,
                activo=True
            )

        except (
            MetodoPago.DoesNotExist,
            ValueError,
            TypeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El método de pago no existe "
                        "o está inactivo."
                    ),
                    "data": None
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # ======================================================
        # EMPRESA
        # ======================================================

        empresa = Empresa.objects.first()

        if not empresa:

            return Response(
                {
                    "success": False,
                    "message": (
                        "No hay configuración de empresa."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        iva_porcentaje = Decimal(
            str(
                empresa.iva
            )
        )

        if not iva_porcentaje.is_finite():

            return Response(
                {
                    "success": False,
                    "message": "El IVA configurado no es válido.",
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ======================================================
        # TRANSACCIÓN
        # ======================================================

        with transaction.atomic():

            # ==================================================
            # SUBTOTAL
            # ==================================================

            subtotal = Decimal(
                "0.00"
            )

            # ==================================================
            # FOLIO
            # ==================================================

            ultima = (
                Venta.objects
                .select_for_update()
                .aggregate(
                    Max("folio")
                )
            )["folio__max"]

            if ultima:

                try:

                    numero = int(
                        ultima.split("-")[1]
                    ) + 1

                except (
                    IndexError,
                    ValueError
                ):

                    return Response(
                        {
                            "success": False,
                            "message": (
                                "No se pudo generar el folio "
                                "de la venta."
                            ),
                            "data": None
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            else:

                numero = 1

            folio = f"V-{numero:07d}"

            # ==================================================
            # CREAR VENTA
            # ==================================================

            venta = Venta.objects.create(

                folio=folio,

                usuario=request.user,

                corte_caja=corte,

                metodo_pago=metodo_pago,

                subtotal=Decimal("0.00"),

                descuento=descuento,

                iva=Decimal("0.00"),

                total=Decimal("0.00"),

            )

            # ==================================================
            # PRODUCTOS
            # ==================================================

            for item in productos:

                # --------------------------------------------------
                # FORMATO
                # --------------------------------------------------

                if not isinstance(
                    item,
                    dict
                ):

                    transaction.set_rollback(
                        True
                    )

                    return Response(
                        {
                            "success": False,
                            "message": (
                                "Cada producto debe "
                                "tener un formato válido."
                            ),
                            "data": None
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # --------------------------------------------------
                # VARIANTE ID
                # --------------------------------------------------

                variante_id = item.get(
                    "variante_id"
                )

                if not variante_id:

                    transaction.set_rollback(
                        True
                    )

                    return Response(
                        {
                            "success": False,
                            "message": (
                                "Cada producto debe indicar "
                                "su variante."
                            ),
                            "data": None
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # --------------------------------------------------
                # CANTIDAD
                # --------------------------------------------------

                try:

                    cantidad = int(
                        item.get(
                            "cantidad"
                        )
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    transaction.set_rollback(
                        True
                    )

                    return Response(
                        {
                            "success": False,
                            "message": (
                                "La cantidad debe ser "
                                "un número entero."
                            ),
                            "data": None
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if cantidad <= 0:

                    transaction.set_rollback(
                        True
                    )

                    return Response(
                        {
                            "success": False,
                            "message": (
                                "La cantidad debe ser "
                                "mayor que cero."
                            ),
                            "data": None
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # ==================================================
                # VARIANTE CON BLOQUEO
                # ==================================================

                try:

                    variante = (
                        Variante.objects
                        .select_for_update()
                        .select_related(
                            "producto"
                        )
                        .get(
                            id=variante_id
                        )
                    )

                except (
                    Variante.DoesNotExist,
                    ValueError,
                    TypeError
                ):

                    transaction.set_rollback(
                        True
                    )

                    return Response(
                        {
                            "success": False,
                            "message": (
                                "La variante no existe."
                            ),
                            "data": None
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )

                # ==================================================
                # VARIANTE ACTIVA
                # ==================================================

                if not variante.activo:

                    transaction.set_rollback(
                        True
                    )

                    return Response(
                        {
                            "success": False,
                            "message": (
                                "La variante está inactiva."
                            ),
                            "data": None
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # ==================================================
                # PRODUCTO ACTIVO
                # ==================================================

                if not variante.producto.activo:

                    transaction.set_rollback(
                        True
                    )

                    return Response(
                        {
                            "success": False,
                            "message": (
                                "El producto está inactivo."
                            ),
                            "data": None
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # ==================================================
                # PRECIO
                # ==================================================

                precio_unitario = Decimal(
                    str(
                        variante.precio_menudeo
                    )
                )

                if not precio_unitario.is_finite():

                    transaction.set_rollback(
                        True
                    )

                    return Response(
                        {
                            "success": False,
                            "message": (
                                "El precio del producto "
                                "no es válido."
                            ),
                            "data": None
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if precio_unitario < 0:

                    transaction.set_rollback(
                        True
                    )

                    return Response(
                        {
                            "success": False,
                            "message": (
                                "El precio del producto "
                                "no puede ser negativo."
                            ),
                            "data": None
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                precio_unitario = precio_unitario.quantize(
                    Decimal("0.01")
                )

                # ==================================================
                # STOCK
                # ==================================================

                stock_anterior = variante.stock
                
                stock_defectuoso_anterior = (
                    variante.stock_defectuoso
                )

                if stock_anterior < cantidad:

                    transaction.set_rollback(
                        True
                    )

                    return Response(
                        {
                            "success": False,
                            "message": "Stock insuficiente.",
                            "data": {
                                "variante_id": str(
                                    variante.id
                                ),
                                "producto": (
                                    variante.producto.nombre
                                ),
                                "variante": (
                                    variante.nombre
                                ),
                                "stock_actual": stock_anterior,
                                "cantidad_solicitada": cantidad
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # ==================================================
                # NUEVO STOCK
                # ==================================================

                stock_nuevo = (
                    stock_anterior -
                    cantidad
                )

                # ==================================================
                # SUBTOTAL LÍNEA
                # ==================================================

                subtotal_linea = (
                    precio_unitario *
                    cantidad
                ).quantize(
                    Decimal("0.01")
                )

                subtotal += subtotal_linea

                # ==================================================
                # DETALLE VENTA
                # ==================================================

                DetalleVenta.objects.create(

                    venta=venta,

                    variante=variante,

                    cantidad=cantidad,

                    precio_unitario=precio_unitario,

                    descuento=Decimal("0.00"),

                    subtotal=subtotal_linea

                )

                # ==================================================
                # MOVIMIENTO INVENTARIO
                # ==================================================

                MovimientoInventario.objects.create(

                    variante=variante,

                    tipo="SALIDA",

                    stock_anterior=stock_anterior,

                    cantidad=cantidad,

                    stock_nuevo=stock_nuevo,
                    
                    stock_defectuoso_nuevo=(
                        stock_defectuoso_anterior
                    ),

                    observaciones=(
                        f"Venta {folio}"
                    ),

                    usuario=request.user

                )

                # ==================================================
                # ACTUALIZAR STOCK
                # ==================================================

                variante.stock = stock_nuevo

                variante.save(
                    update_fields=[
                        "stock",
                        "fecha_actualizacion"
                    ]
                )

            # ==================================================
            # VALIDAR SUBTOTAL
            # ==================================================

            if subtotal <= 0:

                transaction.set_rollback(
                    True
                )

                return Response(
                    {
                        "success": False,
                        "message": (
                            "El subtotal de la venta "
                            "debe ser mayor que cero."
                        ),
                        "data": None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ==================================================
            # VALIDAR DESCUENTO
            # ==================================================

            if descuento > subtotal:

                transaction.set_rollback(
                    True
                )

                return Response(
                    {
                        "success": False,
                        "message": (
                            "El descuento no puede "
                            "ser mayor al subtotal."
                        ),
                        "data": None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ==================================================
            # SUBTOTAL FINAL
            # ==================================================

            subtotal_final = (
                subtotal -
                descuento
            ).quantize(
                Decimal("0.01")
            )

            # ==================================================
            # IVA
            # ==================================================

            iva = (
                subtotal_final *
                (
                    iva_porcentaje /
                    Decimal("100")
                )
            ).quantize(
                Decimal("0.01")
            )

            # ==================================================
            # TOTAL
            # ==================================================

            total = (
                subtotal_final +
                iva
            ).quantize(
                Decimal("0.01")
            )

            # ==================================================
            # ACTUALIZAR VENTA
            # ==================================================

            venta.subtotal = subtotal_final

            venta.descuento = descuento

            venta.iva = iva

            venta.total = total

            venta.save(
                update_fields=[
                    "subtotal",
                    "descuento",
                    "iva",
                    "total"
                ]
            )

            # ==================================================
            # BITÁCORA
            # ==================================================

            registrar_bitacora(

                usuario=request.user,

                modulo="Ventas",

                accion="REGISTRAR_VENTA",

                descripcion=(
                    f"Venta folio {venta.folio} "
                    f"registrada correctamente por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}. "
                    f"Total: ${venta.total}"
                )

            )

            # ==================================================
            # RESPUESTA
            # ==================================================

            return Response(
                {
                    "success": True,
                    "folio": venta.folio,
                    "venta_id": venta.id,
                    "message": (
                        "Venta registrada correctamente."
                    )
                },
                status=status.HTTP_201_CREATED
            )

    # ==========================================================
    # LISTAR VENTAS
    # ==========================================================

    def list(
        self,
        request,
        *args,
        **kwargs
    ):

        ventas = (
            Venta.objects
            .select_related(
                "usuario",
                "metodo_pago",
                "corte_caja",
                "corte_caja__caja"
            )
            .all()
        )

        data = []

        for venta in ventas:

            data.append(
                {
                    "id": venta.id,
                    "folio": venta.folio,
                    "fecha": venta.fecha,
                    "usuario": (
                        venta.usuario.nombre
                    ),
                    "metodo_pago": (
                        venta.metodo_pago.nombre
                    ),
                    "caja": (
                        venta.corte_caja
                        .caja
                        .nombre
                    ),
                    "subtotal": venta.subtotal,
                    "descuento": venta.descuento,
                    "iva": venta.iva,
                    "total": venta.total,
                    "estado": venta.estado,
                }
            )

        return Response(
            {
                "success": True,
                "data": data
            },
            status=status.HTTP_200_OK
        )

    # ==========================================================
    # CONSULTAR VENTA
    # ==========================================================

    def retrieve(
        self,
        request,
        pk=None
    ):

        try:

            venta = (
                Venta.objects
                .select_related(
                    "usuario",
                    "metodo_pago",
                    "corte_caja",
                    "corte_caja__caja"
                )
                .prefetch_related(
                    "detalles__variante__producto"
                )
                .get(
                    pk=pk
                )
            )

        except (
            Venta.DoesNotExist,
            ValueError,
            TypeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "La venta no existe."
                    ),
                    "data": None
                },
                status=status.HTTP_404_NOT_FOUND
            )

        productos = []

        for detalle in venta.detalles.all():

            productos.append(
                {
                    "detalle_id": detalle.id,

                    "producto": (
                        detalle.variante
                        .producto
                        .nombre
                    ),

                    "variante": (
                        detalle.variante
                        .nombre
                    ),

                    "variante_id": (
                        detalle.variante.id
                    ),

                    "cantidad": (
                        detalle.cantidad
                    ),

                    "precio_unitario": (
                        detalle.precio_unitario
                    ),

                    "descuento": (
                        detalle.descuento
                    ),

                    "subtotal": (
                        detalle.subtotal
                    )
                }
            )

        return Response(
            {
                "success": True,

                "data": {

                    "id": venta.id,

                    "folio": venta.folio,

                    "fecha": venta.fecha,

                    "usuario": (
                        venta.usuario.nombre
                    ),

                    "metodo_pago": (
                        venta.metodo_pago.nombre
                    ),

                    "caja": (
                        venta.corte_caja
                        .caja
                        .nombre
                    ),

                    "subtotal": venta.subtotal,

                    "descuento": venta.descuento,

                    "iva": venta.iva,

                    "total": venta.total,

                    "estado": venta.estado,

                    "productos": productos

                }
            },
            status=status.HTTP_200_OK
        )

    # ==========================================================
    # CANCELAR VENTA
    # SOLO ADMINISTRADOR
    # ==========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="cancelar"
    )
    def cancelar(
        self,
        request,
        pk=None
    ):

        # ------------------------------------------------------
        # PERMISOS: admin cancela cualquier venta,
        # empleado solo las suyas.
        # ------------------------------------------------------

        if not request.user.activo:

            return Response(
                {
                    "success": False,
                    "message": "El usuario está inactivo.",
                    "data": None
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # ======================================================
        # TRANSACCIÓN
        # ======================================================

        with transaction.atomic():

            # --------------------------------------------------
            # OBTENER Y BLOQUEAR VENTA
            # --------------------------------------------------

            try:

                venta = (
                    Venta.objects
                    .select_for_update()
                    .get(
                        id=pk
                    )
                )

            except (
                Venta.DoesNotExist,
                ValueError,
                TypeError
            ):

                return Response(
                    {
                        "success": False,
                        "message": (
                            "La venta no existe."
                        ),
                        "data": None
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            # --------------------------------------------------
            # EMPLEADO SOLO PUEDE CANCELAR SUS PROPIAS VENTAS
            # --------------------------------------------------

            if (
                request.user.rol not in (0, 1)
                and venta.usuario_id != request.user.id
            ):

                return Response(
                    {
                        "success": False,
                        "message": (
                            "Solo puedes cancelar "
                            "tus propias ventas."
                        ),
                        "data": None
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            # --------------------------------------------------
            # VALIDAR ESTADO
            # --------------------------------------------------

            if venta.estado == "CANCELADA":

                return Response(
                    {
                        "success": False,
                        "message": (
                            "La venta ya está cancelada."
                        ),
                        "data": None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # --------------------------------------------------
            # NO CANCELAR DEVUELTA
            # --------------------------------------------------

            if venta.estado == "DEVUELTA":

                return Response(
                    {
                        "success": False,
                        "message": (
                            "No se puede cancelar una venta "
                            "que ya fue devuelta completamente."
                        ),
                        "data": None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ==================================================
            # VALIDAR DEVOLUCIONES EXISTENTES
            # ==================================================

            devoluciones_activas = (
                Devolucion.objects
                .filter(
                    venta=venta,
                    estado__in=[
                        "PENDIENTE",
                        "APROBADA"
                    ]
                )
                .exists()
            )

            if devoluciones_activas:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "No se puede cancelar la venta "
                            "porque tiene una devolución "
                            "pendiente o aprobada."
                        ),
                        "data": None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ==================================================
            # OBTENER DETALLES
            # ==================================================

            detalles = (
                venta.detalles
                .select_related(
                    "variante"
                )
                .all()
            )

            # ==================================================
            # RESTAURAR STOCK
            # ==================================================

            for detalle in detalles:

                # ----------------------------------------------
                # BLOQUEAR VARIANTE
                # ----------------------------------------------

                variante = (
                    Variante.objects
                    .select_for_update()
                    .get(
                        id=detalle.variante_id
                    )
                )

                # ----------------------------------------------
                # STOCK ANTERIOR
                # ----------------------------------------------

                stock_anterior = (
                    variante.stock
                )

                # ----------------------------------------------
                # STOCK NUEVO
                # ----------------------------------------------

                stock_nuevo = (
                    stock_anterior +
                    detalle.cantidad
                )
                
                stock_defectuoso_anterior = (
                    variante.stock_defectuoso
                )

                # ----------------------------------------------
                # MOVIMIENTO INVENTARIO
                # ----------------------------------------------

                MovimientoInventario.objects.create(

                    variante=variante,

                    tipo="ENTRADA",

                    stock_anterior=stock_anterior,

                    cantidad=detalle.cantidad,

                    stock_nuevo=stock_nuevo,
                    
                    stock_defectuoso_anterior=(
                    
                    stock_defectuoso_anterior),

                    stock_defectuoso_nuevo=(
                    
                    stock_defectuoso_anterior
                    
                    ),


                    observaciones=(
                        f"Cancelación {venta.folio}"
                    ),

                    usuario=request.user

                )

                # ----------------------------------------------
                # ACTUALIZAR STOCK
                # ----------------------------------------------

                variante.stock = stock_nuevo

                variante.save(
                    update_fields=[
                        "stock",
                        "fecha_actualizacion"
                    ]
                )

            # ==================================================
            # CAMBIAR ESTADO
            # ==================================================

            venta.estado = "CANCELADA"

            venta.save(
                update_fields=[
                    "estado"
                ]
            )

            # ==================================================
            # BITÁCORA
            # ==================================================

            registrar_bitacora(

                usuario=request.user,

                modulo="Ventas",

                accion="CANCELAR_VENTA",

                descripcion=(
                    f"Venta folio {venta.folio} "
                    f"cancelada correctamente por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}. "
                    f"Se restauró el stock "
                    f"de los productos."
                )

            )

        # ======================================================
        # RESPUESTA
        # ======================================================

        return Response(
            {
                "success": True,
                "message": (
                    "Venta cancelada correctamente."
                ),
                "data": None
            },
            status=status.HTTP_200_OK
        )