import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Empresa
from .serializers import EmpresaSerializer

from usuarios.permissions import IsAdmin
from bitacora.services import registrar_bitacora


logger = logging.getLogger(__name__)


class EmpresaView(APIView):

    def get_permissions(self):

        if self.request.method == "GET":
            return [IsAuthenticated()]

        return [
            IsAuthenticated(),
            IsAdmin()
        ]

    def get(self, request):

        empresa = Empresa.objects.first()

        if not empresa:
            return Response(
                {
                    "success": False,
                    "message": "No hay configuración de empresa registrada.",
                    "data": None
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = EmpresaSerializer(empresa)

        return Response(
            {
                "success": True,
                "message": "Configuración de empresa obtenida correctamente.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):

        if Empresa.objects.exists():
            return Response(
                {
                    "success": False,
                    "message": "Ya existe una configuración de empresa. Use PUT para actualizar.",
                    "data": None
                },
                status=status.HTTP_409_CONFLICT
            )

        serializer = EmpresaSerializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "message": "Los datos de la empresa no son válidos.",
                    "data": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            empresa = serializer.save()

            registrar_bitacora(
                usuario=request.user,
                accion="CREAR_EMPRESA",
                descripcion="Se creó la configuración de la empresa."
            )

        except Exception:
            logger.exception(
                "Error al crear configuración de empresa."
            )

            return Response(
                {
                    "success": False,
                    "message": "Error interno del servidor.",
                    "data": None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "success": True,
                "message": "Empresa registrada correctamente.",
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
                    "message": "No hay configuración de empresa registrada.",
                    "data": None
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
                    "message": "Los datos de la empresa no son válidos.",
                    "data": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            empresa = serializer.save()

            registrar_bitacora(
                usuario=request.user,
                accion="ACTUALIZAR_EMPRESA",
                descripcion="Se actualizó la configuración de la empresa."
            )

        except Exception:
            logger.exception(
                "Error al actualizar configuración de empresa."
            )

            return Response(
                {
                    "success": False,
                    "message": "Error interno del servidor.",
                    "data": None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "success": True,
                "message": "Empresa actualizada correctamente.",
                "data": EmpresaSerializer(empresa).data
            },
            status=status.HTTP_200_OK
        )