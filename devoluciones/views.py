from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .permissions import EsAdministrador

from .serializers import (
    CrearDevolucionSerializer,
    DevolucionSerializer
)

from .services import (
    crear_devolucion,
    aprobar_devolucion,
    cambiar_estado_devolucion
)

from .models import Devolucion


class DevolucionListCreateView(APIView):

    permission_classes = [
        IsAuthenticated
    ]


    # GET /api/devoluciones/

    def get(self, request):

        devoluciones = Devolucion.objects.all().order_by(
            "-fecha"
        )

        serializer = DevolucionSerializer(
            devoluciones,
            many=True
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


    # POST /api/devoluciones/

    def post(self, request):

        serializer = CrearDevolucionSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            devolucion = crear_devolucion(
                serializer.validated_data,
                request.user
            )

            response = DevolucionSerializer(
                devolucion
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Devolución registrada correctamente."
                    ),
                    "data": response.data
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class DevolucionDetailView(APIView):

    permission_classes = [
        IsAuthenticated
    ]


    # GET /api/devoluciones/{id}/

    def get(
        self,
        request,
        id
    ):

        try:

            devolucion = Devolucion.objects.get(
                id=id
            )

        except Devolucion.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": (
                        "La devolución no existe."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )


        serializer = DevolucionSerializer(
            devolucion
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


    # PUT /api/devoluciones/{id}/

    def put(
        self,
        request,
        id
    ):

        try:

            devolucion = Devolucion.objects.get(
                id=id
            )

        except Devolucion.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": (
                        "La devolución no existe."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )


        if devolucion.estado != "PENDIENTE":

            return Response(
                {
                    "success": False,
                    "message": (
                        "Solo se pueden modificar "
                        "devoluciones pendientes."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )


        # Por seguridad no permitimos modificar
        # venta, detalles ni total directamente.

        campos_permitidos = [
            "tipo",
            "motivo",
            "metodo_pago_reembolso_id"
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


        if "tipo" in request.data:

            if request.data["tipo"] not in [
                "NORMAL",
                "DEFECTUOSO",
                "GARANTIA",
                "EXTRAORDINARIA"
            ]:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "Tipo de devolución no válido."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            devolucion.tipo = request.data["tipo"]


        if "motivo" in request.data:

            devolucion.motivo = request.data[
                "motivo"
            ]


        if "metodo_pago_reembolso_id" in request.data:

            from metodos_pago.models import MetodoPago

            try:

                metodo = MetodoPago.objects.get(
                    id=request.data[
                        "metodo_pago_reembolso_id"
                    ],
                    activo=True
                )

            except MetodoPago.DoesNotExist:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "El método de reembolso "
                            "no existe o está inactivo."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            devolucion.metodo_pago_reembolso = metodo


        devolucion.save()


        serializer = DevolucionSerializer(
            devolucion
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Devolución actualizada correctamente."
                ),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


class DevolucionAprobarView(APIView):

    permission_classes = [
        IsAuthenticated,
        EsAdministrador
    ]


    # POST /api/devoluciones/{id}/aprobar/

    def post(
        self,
        request,
        id
    ):

        try:

            devolucion = aprobar_devolucion(
                id,
                request.user
            )

            serializer = DevolucionSerializer(
                devolucion
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Devolución aprobada correctamente."
                    ),
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class DevolucionRechazarView(APIView):

    permission_classes = [
        IsAuthenticated,
        EsAdministrador
    ]


    # POST /api/devoluciones/{id}/rechazar/

    def post(
        self,
        request,
        id
    ):

        try:

            devolucion = cambiar_estado_devolucion(
                id,
                "RECHAZADA",
                request.user
            )

            serializer = DevolucionSerializer(
                devolucion
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Devolución rechazada correctamente."
                    ),
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )