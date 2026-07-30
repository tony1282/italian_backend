from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Empresa
from .serializers import EmpresaSerializer


class EmpresaView(APIView):

    permission_classes = [IsAuthenticated]


    def get(self, request):

        empresa = Empresa.objects.first()

        if not empresa:

            return Response(
                {
                    "success": False,
                    "message": "No hay configuración de empresa registrada."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = EmpresaSerializer(empresa)

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


    def post(self, request):

        if Empresa.objects.exists():

            return Response(
                {
                    "success": False,
                    "message": "Ya existe una configuración de empresa. Use PUT para actualizar."
                },
                status=status.HTTP_409_CONFLICT
            )


        serializer = EmpresaSerializer(data=request.data)

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        empresa = serializer.save()


        return Response(
            {
                "success": True,
                "message": "Configuración de empresa guardada correctamente.",
                "data": EmpresaSerializer(empresa).data
            },
            status=status.HTTP_201_CREATED
        )


    def put(self, request):

        empresa = Empresa.objects.first()


        if not empresa:

            return Response(
                {
                    "success": False,
                    "message": "No existe configuración de empresa para actualizar."
                },
                status=status.HTTP_404_NOT_FOUND
            )


        serializer = EmpresaSerializer(
            empresa,
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


        empresa = serializer.save()


        return Response(
            {
                "success": True,
                "message": "Configuración de empresa actualizada correctamente.",
                "data": EmpresaSerializer(empresa).data
            },
            status=status.HTTP_200_OK
        )