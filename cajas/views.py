from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Caja
from .serializers import CajaSerializer


class CajaViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):

    queryset = Caja.objects.all()

    serializer_class = CajaSerializer

    permission_classes = []


    def list(self, request):

        cajas = self.get_queryset()

        serializer = self.get_serializer(
            cajas,
            many=True
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


    def create(self, request):

        nombre = request.data.get("nombre")


        if Caja.objects.filter(
            nombre__iexact=nombre
        ).exists():

            return Response(
                {
                    "success": False,
                    "message": "Ya existe una caja con ese nombre."
                },
                status=status.HTTP_409_CONFLICT
            )


        serializer = self.get_serializer(
            data=request.data
        )


        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        caja = serializer.save()


        return Response(
            {
                "success": True,
                "message": "Caja creada correctamente.",
                "data": {
                    "id": caja.id
                }
            },
            status=status.HTTP_201_CREATED
        )


    @action(
        detail=False,
        methods=["get"]
    )
    def activas(self, request):

        cajas = Caja.objects.filter(
            activa=True
        )


        data = [
            {
                "id": caja.id,
                "nombre": caja.nombre,
                "estado": caja.estado
            }

            for caja in cajas
        ]


        return Response(
            {
                "success": True,
                "data": data
            },
            status=status.HTTP_200_OK
        ) 
        