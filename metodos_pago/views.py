from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import MetodoPago
from .serializers import MetodoPagoSerializer


class MetodoPagoView(APIView):

    permission_classes = []


    # GET /api/metodos-pago/
    # Lista todos los métodos (activos e inactivos)

    def get(self, request):

        metodos = MetodoPago.objects.all()

        serializer = MetodoPagoSerializer(
            metodos,
            many=True
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


    # POST /api/metodos-pago/
    # Crear método de pago

    def post(self, request):

        nombre = request.data.get("nombre")


        if MetodoPago.objects.filter(
            nombre__iexact=nombre
        ).exists():

            return Response(
                {
                    "success": False,
                    "message": "Ya existe un método de pago con ese nombre."
                },
                status=status.HTTP_409_CONFLICT
            )


        serializer = MetodoPagoSerializer(
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


        metodo = serializer.save()


        return Response(
            {
                "success": True,
                "message": "Método de pago creado correctamente.",
                "data": {
                    "id": metodo.id
                }
            },
            status=status.HTTP_201_CREATED
        )



    # PUT /api/metodos-pago/{id}/
    # Actualizar nombre o estado

    def put(self, request, id):

        try:

            metodo = MetodoPago.objects.get(
                id=id
            )

        except MetodoPago.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "Método de pago no encontrado."
                },
                status=status.HTTP_404_NOT_FOUND
            )


        nuevo_nombre = request.data.get(
            "nombre",
            metodo.nombre
        )


        if MetodoPago.objects.filter(
            nombre__iexact=nuevo_nombre
        ).exclude(
            id=id
        ).exists():

            return Response(
                {
                    "success": False,
                    "message": "Ya existe un método de pago con ese nombre."
                },
                status=status.HTTP_409_CONFLICT
            )


        serializer = MetodoPagoSerializer(
            metodo,
            data=request.data,
            partial=True
        )


        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        serializer.save()


        return Response(
            {
                "success": True,
                "message": "Método de pago actualizado correctamente.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )



    # DELETE /api/metodos-pago/{id}/
    # Eliminación lógica

    def delete(self, request, id):

        try:

            metodo = MetodoPago.objects.get(
                id=id
            )


        except MetodoPago.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "Método de pago no encontrado."
                },
                status=status.HTTP_404_NOT_FOUND
            )


        metodo.activo = False
        metodo.save()


        return Response(
            {
                "success": True,
                "message": "Método de pago desactivado correctamente."
            },
            status=status.HTTP_200_OK
        )



class MetodoPagoActivoView(APIView):

    permission_classes = []


    # GET /api/metodos-pago/activos/

    def get(self, request):

        metodos = MetodoPago.objects.filter(
            activo=True
        )


        data = [
            {
                "id": metodo.id,
                "nombre": metodo.nombre
            }

            for metodo in metodos
        ]


        return Response(
            {
                "success": True,
                "data": data
            },
            status=status.HTTP_200_OK
        )