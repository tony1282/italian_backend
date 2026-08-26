from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from .models import MovimientoInventario
from .serializers import MovimientoInventarioSerializer

from variantes.models import Variante

from bitacora.services import registrar_bitacora


class MovimientoInventarioViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):

    queryset = MovimientoInventario.objects.all()

    serializer_class = MovimientoInventarioSerializer

    permission_classes = [IsAuthenticated]


    @action(
        detail=False,
        methods=["post"]
    )
    def entrada(self, request):

        variante_id = request.data.get("variante_id")
        observaciones = request.data.get("observaciones")

        try:
            cantidad = int(request.data.get("cantidad"))
        
        except (TypeError, ValueError):
            return Response(
                {   
                    "success": False,
                    "message": "La cantidad debe ser un número entero."    
                    
                 },
                status=status.HTTP_400_BAD_REQUEST
                )

        if cantidad <= 0: 
            return Response(
                {
                    "success": False,
                    "message": "La cantidad debe ser mayor a cero"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            variante = Variante.objects.get(
                id=variante_id
            )

        except Variante.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "La variante no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )


        with transaction.atomic():

            movimiento = MovimientoInventario.objects.create(
                variante=variante,
                tipo="ENTRADA",
                cantidad=cantidad,
                observaciones=observaciones,
                usuario=request.user
            )


            variante.stock += cantidad
            variante.save()


            # ==========================================
            # BITÁCORA
            # ==========================================

            registrar_bitacora(

                usuario=request.user,

                modulo="Inventario",

                accion="ENTRADA_INVENTARIO",

                descripcion=(
                    f"Entrada de inventario registrada para "
                    f"la variante '{variante.nombre}' por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}. "
                    f"Cantidad ingresada: {cantidad}. "
                    f"Stock actual: {variante.stock}."
                )

            )


        return Response(
            {
                "success": True,
                "message": "Movimiento de inventario registrado correctamente.",
                "data": {
                    "id": movimiento.id
                }
            },
            status=status.HTTP_201_CREATED
        )


    @action(
        detail=False,
        methods=["post"]
    )
    def salida(self, request):

        variante_id = request.data.get("variante_id")
        observaciones = request.data.get("observaciones")
        
        try:
            cantidad = int(request.data.get("cantidad"))

        except (TypeError, ValueError):

            return Response (
                {
                    "success": False,
                    "message": "La cantidad debe ser un número entero"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if cantidad <= 0:

            return Response (
                {
                    "success" : False,
                    "message" : "La cantidad debe ser mayor a cero"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            variante = Variante.objects.get(
                id=variante_id
            )

        except Variante.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "La variante no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )


        if variante.stock < cantidad:

            return Response(
                {
                    "success": False,
                    "message": "Stock insuficiente."
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        with transaction.atomic():

            movimiento = MovimientoInventario.objects.create(
                variante=variante,
                tipo="SALIDA",
                cantidad=cantidad,
                observaciones=observaciones,
                usuario=request.user
            )


            variante.stock -= cantidad
            variante.save()


            # ==========================================
            # BITÁCORA
            # ==========================================

            registrar_bitacora(

                usuario=request.user,

                modulo="Inventario",

                accion="SALIDA_INVENTARIO",

                descripcion=(
                    f"Salida de inventario registrada para "
                    f"la variante '{variante.nombre}' por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}. "
                    f"Cantidad retirada: {cantidad}. "
                    f"Stock actual: {variante.stock}."
                )

            )


        return Response(
            {
                "success": True,
                "message": "Movimiento de inventario registrado correctamente.",
                "data": {
                    "id": movimiento.id
                }
            },
            status=status.HTTP_201_CREATED
        )


    @action(
        detail=False,
        methods=["post"]
    )
    def ajuste(self, request):

        variante_id = request.data.get("variante_id")
        observaciones = request.data.get("observaciones")

        try:
            cantidad = int(request.data.get("cantidad"))
            
        except (ValueError, TypeError):

            return Response (
                {
                    "success" : False,
                    "message" : "La cantidad debe ser un número entero."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if cantidad <= 0:

            return Response (
                {
                    "success": False,
                    "message": "La cantidad debe ser mayor a cero."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            variante = Variante.objects.get(
                id=variante_id
            )

        except Variante.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "La variante no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )


        with transaction.atomic():

            movimiento = MovimientoInventario.objects.create(
                variante=variante,
                tipo="AJUSTE",
                cantidad=cantidad,
                observaciones=observaciones,
                usuario=request.user
            )


            variante.stock = cantidad
            variante.save()


            # ==========================================
            # BITÁCORA
            # ==========================================

            registrar_bitacora(

                usuario=request.user,

                modulo="Inventario",

                accion="AJUSTE_INVENTARIO",

                descripcion=(
                    f"Ajuste de inventario realizado para "
                    f"la variante '{variante.nombre}' por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}. "
                    f"Nuevo stock: {cantidad}."
                )

            )


        return Response(
            {
                "success": True,
                "message": "Movimiento de inventario registrado correctamente.",
                "data" : {
                    "id": movimiento.id
                }
            },
            status=status.HTTP_201_CREATED
        )