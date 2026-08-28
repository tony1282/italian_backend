from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from usuarios.permissions import IsAdmin

from .models import MetodoPago
from .serializers import MetodoPagoSerializer


class MetodoPagoView(APIView):

    def get_permissions(self):

        if self.request.method == "GET":

            return [
                IsAuthenticated()
            ]

        return [
            IsAuthenticated(),
            IsAdmin()
        ]


    # GET /api/metodos-pago/
    # Lista todos los métodos

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
    # Los métodos son fijos

    def post(self, request):

        return Response(
            {
                "success": False,
                "message": (
                    "Los métodos de pago son fijos "
                    "y no pueden crearse."
                )
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


    # PUT /api/metodos-pago/{id}/
    # Solamente permite activar/desactivar

    def put(self, request, id):

        try:

            metodo = MetodoPago.objects.get(
                id=id
            )

        except MetodoPago.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Método de pago no encontrado."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )


        campos_permitidos = [
            "activo"
        ]


        for campo in request.data:

            if campo not in campos_permitidos:

                return Response(
                    {
                        "success": False,
                        "message": (
                            f"El campo '{campo}' "
                            "no puede modificarse."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )


        if "activo" not in request.data:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Debe indicar el estado "
                        "activo del método."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        metodo.activo = request.data["activo"]

        metodo.save(
            update_fields=[
                "activo",
                "fecha_actualizacion"
            ]
        )


        serializer = MetodoPagoSerializer(
            metodo
        )


        return Response(
            {
                "success": True,
                "message": (
                    "Método de pago actualizado correctamente."
                ),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


    # DELETE /api/metodos-pago/{id}/
    # Desactivar método

    def delete(self, request, id):

        try:

            metodo = MetodoPago.objects.get(
                id=id
            )

        except MetodoPago.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Método de pago no encontrado."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )


        metodo.activo = False

        metodo.save(
            update_fields=[
                "activo",
                "fecha_actualizacion"
            ]
        )


        return Response(
            {
                "success": True,
                "message": (
                    "Método de pago desactivado correctamente."
                )
            },
            status=status.HTTP_200_OK
        )


class MetodoPagoActivoView(APIView):

    permission_classes = [
        IsAuthenticated
    ]


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