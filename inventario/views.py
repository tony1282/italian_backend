import uuid

from rest_framework import (
    viewsets,
    mixins,
    status
)

from rest_framework.decorators import action

from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated

from django.db import transaction

from .models import MovimientoInventario

from .serializers import MovimientoInventarioSerializer

from variantes.models import Variante

from usuarios.permissions import IsAdmin

from bitacora.services import registrar_bitacora


class MovimientoInventarioViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):

    queryset = (
        MovimientoInventario.objects
        .select_related(
            "variante",
            "variante__producto",
            "usuario"
        )
        .all()
        .order_by("-fecha")
    )

    serializer_class = MovimientoInventarioSerializer

    permission_classes = [
        IsAuthenticated
    ]

    # ==========================================================
    # ENTRADA
    # ==========================================================

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAdmin]
    )
    def entrada(self, request):

        variante_id = request.data.get(
            "variante_id"
        )

        observaciones = request.data.get(
            "observaciones"
        )

        try:

            cantidad = int(
                request.data.get(
                    "cantidad"
                )
            )

        except (
            TypeError,
            ValueError
        ):

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

            return Response(
                {
                    "success": False,
                    "message": (
                        "La cantidad debe ser "
                        "mayor a cero."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            uuid.UUID(
                str(variante_id)
            )

        except (
            TypeError,
            ValueError,
            AttributeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El identificador de la "
                        "variante no es válido."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            try:

                variante = (
                    Variante.objects
                    .select_for_update()
                    .get(
                        id=variante_id
                    )
                )

            except Variante.DoesNotExist:

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

            stock_anterior = variante.stock

            stock_nuevo = (
                stock_anterior
                +
                cantidad
            )

            stock_defectuoso_anterior = (
                variante.stock_defectuoso
            )

            stock_defectuoso_nuevo = (
                stock_defectuoso_anterior
            )

            movimiento = (
                MovimientoInventario.objects.create(

                    variante=variante,

                    tipo="ENTRADA",

                    stock_anterior=stock_anterior,

                    cantidad=cantidad,

                    stock_nuevo=stock_nuevo,

                    stock_defectuoso_anterior=(
                        stock_defectuoso_anterior
                    ),

                    stock_defectuoso_nuevo=(
                        stock_defectuoso_nuevo
                    ),

                    observaciones=observaciones,

                    usuario=request.user

                )
            )

            variante.stock = stock_nuevo

            variante.save(
                update_fields=[
                    "stock",
                    "fecha_actualizacion"
                ]
            )

            registrar_bitacora(

                usuario=request.user,

                modulo="Inventario",

                accion="ENTRADA_INVENTARIO",

                descripcion=(
                    f"Entrada de inventario registrada "
                    f"para la variante "
                    f"'{variante.nombre}' por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}. "
                    f"Stock anterior: "
                    f"{stock_anterior}. "
                    f"Cantidad ingresada: "
                    f"{cantidad}. "
                    f"Stock nuevo: "
                    f"{stock_nuevo}."
                )
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Movimiento de inventario "
                    "registrado correctamente."
                ),
                "data": {

                    "id": movimiento.id,

                    "tipo": movimiento.tipo,

                    "stock_anterior":
                        stock_anterior,

                    "cantidad":
                        cantidad,

                    "stock_nuevo":
                        stock_nuevo,

                    "stock_defectuoso_anterior":
                        stock_defectuoso_anterior,

                    "stock_defectuoso_nuevo":
                        stock_defectuoso_nuevo
                }
            },
            status=status.HTTP_201_CREATED
        )

    # ==========================================================
    # SALIDA
    # ==========================================================

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAdmin]
    )
    def salida(self, request):

        variante_id = request.data.get(
            "variante_id"
        )

        observaciones = request.data.get(
            "observaciones"
        )

        try:

            cantidad = int(
                request.data.get(
                    "cantidad"
                )
            )

        except (
            TypeError,
            ValueError
        ):

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

            return Response(
                {
                    "success": False,
                    "message": (
                        "La cantidad debe ser "
                        "mayor a cero."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            uuid.UUID(
                str(variante_id)
            )

        except (
            TypeError,
            ValueError,
            AttributeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El identificador de la "
                        "variante no es válido."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            try:

                variante = (
                    Variante.objects
                    .select_for_update()
                    .get(
                        id=variante_id
                    )
                )

            except Variante.DoesNotExist:

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

            stock_anterior = variante.stock

            if stock_anterior < cantidad:

                return Response(
                    {
                        "success": False,
                        "message": "Stock insuficiente.",
                        "data": {

                            "stock_actual":
                                stock_anterior,

                            "cantidad_solicitada":
                                cantidad
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            stock_nuevo = (
                stock_anterior
                -
                cantidad
            )

            stock_defectuoso_anterior = (
                variante.stock_defectuoso
            )

            stock_defectuoso_nuevo = (
                stock_defectuoso_anterior
            )

            movimiento = (
                MovimientoInventario.objects.create(

                    variante=variante,

                    tipo="SALIDA",

                    stock_anterior=stock_anterior,

                    cantidad=cantidad,

                    stock_nuevo=stock_nuevo,

                    stock_defectuoso_anterior=(
                        stock_defectuoso_anterior
                    ),

                    stock_defectuoso_nuevo=(
                        stock_defectuoso_nuevo
                    ),

                    observaciones=observaciones,

                    usuario=request.user

                )
            )

            variante.stock = stock_nuevo

            variante.save(
                update_fields=[
                    "stock",
                    "fecha_actualizacion"
                ]
            )

            registrar_bitacora(

                usuario=request.user,

                modulo="Inventario",

                accion="SALIDA_INVENTARIO",

                descripcion=(
                    f"Salida de inventario registrada "
                    f"para la variante "
                    f"'{variante.nombre}' por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}. "
                    f"Stock anterior: "
                    f"{stock_anterior}. "
                    f"Cantidad retirada: "
                    f"{cantidad}. "
                    f"Stock nuevo: "
                    f"{stock_nuevo}."
                )
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Movimiento de inventario "
                    "registrado correctamente."
                ),
                "data": {

                    "id": movimiento.id,

                    "tipo": movimiento.tipo,

                    "stock_anterior":
                        stock_anterior,

                    "cantidad":
                        cantidad,

                    "stock_nuevo":
                        stock_nuevo,

                    "stock_defectuoso_anterior":
                        stock_defectuoso_anterior,

                    "stock_defectuoso_nuevo":
                        stock_defectuoso_nuevo
                }
            },
            status=status.HTTP_201_CREATED
        )

    # ==========================================================
    # AJUSTE
    # ==========================================================

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAdmin]
    )
    def ajuste(self, request):

        variante_id = request.data.get(
            "variante_id"
        )

        stock_nuevo_solicitado = request.data.get(
            "stock_nuevo"
        )

        observaciones = request.data.get(
            "observaciones"
        )

        # ======================================================
        # VALIDAR STOCK NUEVO
        # ======================================================

        try:

            stock_nuevo_solicitado = int(
                stock_nuevo_solicitado
            )

        except (
            TypeError,
            ValueError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El stock nuevo debe ser "
                        "un número entero."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if stock_nuevo_solicitado < 0:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El stock no puede ser negativo."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ======================================================
        # VALIDAR VARIANTE ID
        # ======================================================

        try:

            uuid.UUID(
                str(variante_id)
            )

        except (
            TypeError,
            ValueError,
            AttributeError
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "El identificador de la "
                        "variante no es válido."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ======================================================
        # TRANSACCIÓN
        # ======================================================

        with transaction.atomic():

            # ==================================================
            # BLOQUEAR VARIANTE
            # ==================================================

            try:

                variante = (
                    Variante.objects
                    .select_for_update()
                    .get(
                        id=variante_id
                    )
                )

            except Variante.DoesNotExist:

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
            # STOCK ANTERIOR
            # ==================================================

            stock_anterior = variante.stock

            # ==================================================
            # CALCULAR DIFERENCIA
            # ==================================================

            diferencia = (
                stock_nuevo_solicitado
                -
                stock_anterior
            )

            # ==================================================
            # NO PERMITIR AJUSTE SIN CAMBIO
            # ==================================================

            if diferencia == 0:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "El stock nuevo es igual al "
                            "stock actual. No hay nada "
                            "que ajustar."
                        ),
                        "data": None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ==================================================
            # CANTIDAD DEL MOVIMIENTO
            # ==================================================

            cantidad = abs(
                diferencia
            )

            # ==================================================
            # STOCK DEFECTUOSO
            # ==================================================

            stock_defectuoso_anterior = (
                variante.stock_defectuoso
            )

            stock_defectuoso_nuevo = (
                stock_defectuoso_anterior
            )

            # ==================================================
            # TIPO DE AJUSTE
            # ==================================================

            if diferencia > 0:

                tipo_ajuste = "AUMENTO"

            else:

                tipo_ajuste = "DISMINUCIÓN"

            # ==================================================
            # OBSERVACIÓN AUTOMÁTICA
            # ==================================================

            observacion_final = (
                f"{tipo_ajuste} de stock. "
                f"{observaciones}"
                if observaciones
                else f"{tipo_ajuste} de stock."
            )

            # ==================================================
            # CREAR MOVIMIENTO
            # ==================================================

            movimiento = (
                MovimientoInventario.objects.create(

                    variante=variante,

                    tipo="AJUSTE",

                    stock_anterior=stock_anterior,

                    cantidad=cantidad,

                    stock_nuevo=stock_nuevo_solicitado,

                    stock_defectuoso_anterior=(
                        stock_defectuoso_anterior
                    ),

                    stock_defectuoso_nuevo=(
                        stock_defectuoso_nuevo
                    ),

                    observaciones=(
                        observacion_final
                    ),

                    usuario=request.user

                )
            )

            # ==================================================
            # ACTUALIZAR STOCK
            # ==================================================

            variante.stock = (
                stock_nuevo_solicitado
            )

            variante.save(
                update_fields=[
                    "stock",
                    "fecha_actualizacion"
                ]
            )

            # ==================================================
            # BITÁCORA
            # ==================================================

            registrar_bitacora(

                usuario=request.user,

                modulo="Inventario",

                accion="AJUSTE_INVENTARIO",

                descripcion=(
                    f"Ajuste de inventario realizado "
                    f"para la variante "
                    f"'{variante.nombre}' por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}. "

                    f"Stock anterior: "
                    f"{stock_anterior}. "

                    f"Cantidad ajustada: "
                    f"{cantidad}. "

                    f"Stock nuevo: "
                    f"{stock_nuevo_solicitado}. "

                    f"Tipo de ajuste: "
                    f"{tipo_ajuste}."
                )
            )

        # ======================================================
        # RESPUESTA
        # ======================================================

        return Response(
            {
                "success": True,
                "message": (
                    "Ajuste de inventario "
                    "registrado correctamente."
                ),
                "data": {

                    "id":
                        movimiento.id,

                    "tipo":
                        movimiento.tipo,

                    "stock_anterior":
                        stock_anterior,

                    "cantidad":
                        cantidad,

                    "stock_nuevo":
                        stock_nuevo_solicitado,

                    "stock_defectuoso_anterior":
                        stock_defectuoso_anterior,

                    "stock_defectuoso_nuevo":
                        stock_defectuoso_nuevo,

                    "tipo_ajuste":
                        tipo_ajuste
                }
            },
            status=status.HTTP_201_CREATED
        )