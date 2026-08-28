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
                request.data.get("cantidad")
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
                stock_anterior + cantidad
            )

            movimiento = (
                MovimientoInventario.objects.create(
                    variante=variante,
                    tipo="ENTRADA",
                    stock_anterior=stock_anterior,
                    cantidad=cantidad,
                    stock_nuevo=stock_nuevo,
                    observaciones=observaciones,
                    usuario=request.user
                )
            )

            variante.stock = stock_nuevo

            variante.save(
                update_fields=["stock"]
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
                    "stock_anterior": stock_anterior,
                    "cantidad": cantidad,
                    "stock_nuevo": stock_nuevo
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
                request.data.get("cantidad")
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
                            "stock_actual": stock_anterior,
                            "cantidad_solicitada": cantidad
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            stock_nuevo = (
                stock_anterior - cantidad
            )

            movimiento = (
                MovimientoInventario.objects.create(
                    variante=variante,
                    tipo="SALIDA",
                    stock_anterior=stock_anterior,
                    cantidad=cantidad,
                    stock_nuevo=stock_nuevo,
                    observaciones=observaciones,
                    usuario=request.user
                )
            )

            variante.stock = stock_nuevo

            variante.save(
                update_fields=["stock"]
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
                    "stock_anterior": stock_anterior,
                    "cantidad": cantidad,
                    "stock_nuevo": stock_nuevo
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

        observaciones = request.data.get(
            "observaciones"
        )

        try:

            cantidad = int(
                request.data.get("cantidad")
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

        if cantidad < 0:

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

            stock_nuevo = cantidad

            movimiento = (
                MovimientoInventario.objects.create(
                    variante=variante,
                    tipo="AJUSTE",
                    stock_anterior=stock_anterior,
                    cantidad=cantidad,
                    stock_nuevo=stock_nuevo,
                    observaciones=observaciones,
                    usuario=request.user
                )
            )

            variante.stock = stock_nuevo

            variante.save(
                update_fields=["stock"]
            )

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
                    "stock_anterior": stock_anterior,
                    "cantidad": cantidad,
                    "stock_nuevo": stock_nuevo
                }
            },
            status=status.HTTP_201_CREATED
        )