from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Empresa
from .serializers import EmpresaSerializer
from .permissions import EsAdministrador

from bitacora.services import registrar_bitacora


class EmpresaView(APIView):

    def get_permissions(self):

        if self.request.method == "GET":

            return [
                IsAuthenticated()
            ]

        return [
            IsAuthenticated(),
            EsAdministrador()
        ]


    def get(self, request):

        empresa = Empresa.objects.first()

        if not empresa:

            return Response(
                {
                    "success": False,
                    "message": (
                        "No hay configuración de empresa "
                        "registrada."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = EmpresaSerializer(
            empresa
        )

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
                    "message": (
                        "Ya existe una configuración de empresa. "
                        "Use PUT para actualizar."
                    )
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
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        empresa = serializer.save()


        # ========================================================
        # BITÁCORA
        # ========================================================

        registrar_bitacora(

            usuario=request.user,

            modulo="Empresa",

            accion="CREAR_EMPRESA",

            descripcion=(
                f"Configuración de empresa "
                f"'{empresa.nombre}' creada por "
                f"{request.user.nombre} "
                f"{request.user.apellido}. "
                f"RFC: {empresa.rfc or 'No especificado'}. "
                f"Días de devolución: "
                f"{empresa.dias_devolucion}. "
                f"IVA: {empresa.iva}%."
            )

        )


        return Response(
            {
                "success": True,
                "message": (
                    "Configuración de empresa "
                    "guardada correctamente."
                ),
                "data": EmpresaSerializer(
                    empresa
                ).data
            },
            status=status.HTTP_201_CREATED
        )


    def put(self, request):

        empresa = Empresa.objects.first()


        if not empresa:

            return Response(
                {
                    "success": False,
                    "message": (
                        "No existe configuración de empresa "
                        "para actualizar."
                    )
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


        # ========================================================
        # BITÁCORA
        # ========================================================

        registrar_bitacora(

            usuario=request.user,

            modulo="Empresa",

            accion="ACTUALIZAR_EMPRESA",

            descripcion=(
                f"Configuración de empresa "
                f"'{empresa.nombre}' actualizada por "
                f"{request.user.nombre} "
                f"{request.user.apellido}. "
                f"RFC: {empresa.rfc or 'No especificado'}. "
                f"Días de devolución: "
                f"{empresa.dias_devolucion}. "
                f"IVA: {empresa.iva}%."
            )

        )


        return Response(
            {
                "success": True,
                "message": (
                    "Configuración de empresa "
                    "actualizada correctamente."
                ),
                "data": EmpresaSerializer(
                    empresa
                ).data
            },
            status=status.HTTP_200_OK
        )