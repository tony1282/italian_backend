from rest_framework import (
    mixins,
    viewsets,
    status
)

from rest_framework.decorators import action

from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated

from django.utils import timezone

from django.db import transaction


from .models import CorteCaja, MovimientoCaja

from .serializers import (CorteCajaSerializer, MovimientoCajaSerializer)

from cajas.models import Caja



class CorteCajaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):


    queryset = CorteCaja.objects.all()


    serializer_class = CorteCajaSerializer


    permission_classes = [
        IsAuthenticated
    ]



    # POST /api/caja/abrir/

    @action(
        detail=False,
        methods=["post"],
        url_path="abrir"
    )
    def abrir(self, request):


        caja_id = request.data.get(
            "caja_id"
        )


        efectivo_inicial = request.data.get(
            "efectivo_inicial"
        )


        try:

            caja = Caja.objects.get(
                id=caja_id
            )


        except Caja.DoesNotExist:

            return Response(
                {
                    "success":False,
                    "message":
                    "La caja no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )



        corte_abierto = CorteCaja.objects.filter(

            caja=caja,

            fecha_fin__isnull=True

        ).exists()



        if corte_abierto:

            return Response(
                {
                    "success":False,
                    "message":
                    "Ya existe un corte abierto para esta caja."
                },
                status=status.HTTP_400_BAD_REQUEST
            )



        if efectivo_inicial is None:

            return Response(
                {
                    "success":False,
                    "message":
                    "El efectivo inicial es obligatorio."
                },
                status=status.HTTP_400_BAD_REQUEST
            )



        with transaction.atomic():


            corte = CorteCaja.objects.create(

                caja=caja,

                usuario=request.user,

                efectivo_inicial=efectivo_inicial

            )



            caja.estado = "ABIERTA"

            caja.save()



        return Response(
            {
                "success":True,

                "message":
                "Caja abierta correctamente.",

                "data":
                {
                    "corte_id":corte.id,

                    "fecha_inicio":
                    corte.fecha_inicio
                }
            },

            status=status.HTTP_201_CREATED
        )



    # POST /api/caja/cerrar/

    @action(
        detail=False,
        methods=["post"],
        url_path="cerrar"
    )
    def cerrar(self, request):


        caja_id = request.data.get(
            "caja_id"
        )


        efectivo_final = request.data.get(
            "efectivo_final"
        )


        try:

            corte = CorteCaja.objects.get(

                caja_id=caja_id,

                fecha_fin__isnull=True

            )


        except CorteCaja.DoesNotExist:


            return Response(
                {
                    "success":False,

                    "message":
                    "No existe un corte abierto."
                },
                status=status.HTTP_404_NOT_FOUND
            )



        if efectivo_final is None:

            return Response(
                {
                    "success":False,

                    "message":
                    "El efectivo final es obligatorio."
                },
                status=status.HTTP_400_BAD_REQUEST
            )



        # Pendiente conectar con Venta y Devoluciones

        total_ventas_efectivo = 0

        total_reembolsos_efectivo = 0



        efectivo_esperado = (

            corte.efectivo_inicial

            +

            total_ventas_efectivo

            -

            total_reembolsos_efectivo

        )


        diferencia = (

            efectivo_final

            -

            efectivo_esperado

        )



        with transaction.atomic():


            corte.efectivo_final = efectivo_final

            corte.diferencia = diferencia

            corte.fecha_fin = timezone.now()

            corte.save()



            corte.caja.estado = "CERRADA"

            corte.caja.save()



        return Response(
            {
                "success":True,

                "message":
                "Caja cerrada correctamente.",

                "data":
                {
                    "corte_id":corte.id,

                    "efectivo_esperado":
                    efectivo_esperado,

                    "efectivo_contado":
                    efectivo_final,

                    "diferencia":
                    diferencia
                }
            }
        )



    # GET /api/caja/corte/activo/

    @action(
        detail=False,
        methods=["get"],
        url_path="corte/activo"
    )
    def activo(self, request):


        corte = CorteCaja.objects.filter(

            fecha_fin__isnull=True

        ).first()



        if not corte:

            return Response(
                {
                    "success":False,

                    "message":
                    "No existe un corte abierto."
                },
                status=status.HTTP_404_NOT_FOUND
            )



        serializer = self.get_serializer(
            corte
        )


        return Response(
            {
                "success":True,
                "data":serializer.data
            }
        )



    # GET /api/cajas/{id}/cortes/

    @action(
        detail=False,
        methods=["get"],
        url_path="cajas/(?P<caja_id>[^/.]+)/cortes"
    )
    def historial(self, request, caja_id):


        cortes = CorteCaja.objects.filter(

            caja_id=caja_id

        ).order_by(
            "-fecha_inicio"
        )



        serializer = self.get_serializer(
            cortes,
            many=True
        )


        return Response(
            {
                "success":True,
                "data":serializer.data
            }
        )
        
    
    @action(
        detail=True,
        methods=["get"],
        url_path="movimientos"
    )
    def movimiento(self, request, pk=None):


        corte = self.get_object()
        
        movimientos = MovimientoCaja.objects.filter(
            corte_caja=corte
        ).order_by(
            "-fecha"
        )
        
        serializer = MovimientoCajaSerializer(
            movimientos,
            many=True
        )
        
        return Response(
            {
                "success":True,
                "data":serializer.data
            },
            status=status.HTTP_200_OK
        )