from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from usuarios.permissions import IsAdmin

from .models import Garantia
from .serializers import (
    CrearGarantiaSerializer,
    AprobarGarantiaSerializer,
    RechazarGarantiaSerializer,
    FinalizarGarantiaSerializer,
    GarantiaSerializer,
)
from .services import (
    crear_garantia,
    aprobar_garantia,
    rechazar_garantia,
    finalizar_garantia,
)


class GarantiaListCreateView(APIView):

    permission_classes = [IsAuthenticated]

    # GET /api/garantias/
    def get(self, request):

        garantias = Garantia.objects.select_related(
            "venta",
            "detalle_venta",
            "variante",
            "variante__producto",
            "usuario",
            "variante_nueva"
        ).all()

        serializer = GarantiaSerializer(
            garantias,
            many=True
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    # POST /api/garantias/
    def post(self, request):

        serializer = CrearGarantiaSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            garantia = crear_garantia(
                serializer.validated_data,
                request.user
            )

            return Response(
                {
                    "success": True,
                    "message": "Garantía registrada correctamente.",
                    "data": GarantiaSerializer(garantia).data
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


class GarantiaDetailView(APIView):

    permission_classes = [IsAuthenticated]

    # GET /api/garantias/<id>/
    def get(self, request, id):

        try:

            garantia = (
                Garantia.objects
                .select_related(
                    "venta",
                    "detalle_venta",
                    "variante",
                    "variante__producto",
                    "usuario",
                    "variante_nueva"
                )
                .get(id=id)
            )

        except Garantia.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "La garantía no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "success": True,
                "data": GarantiaSerializer(garantia).data
            },
            status=status.HTTP_200_OK
        )

    # PUT /api/garantias/<id>/
    def put(self, request, id):

        try:

            garantia = Garantia.objects.get(
                id=id
            )

        except Garantia.DoesNotExist:

            return Response(
                {
                    "success": False,
                    "message": "La garantía no existe."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Solo se pueden modificar garantías pendientes
        if garantia.estado != "PENDIENTE":

            return Response(
                {
                    "success": False,
                    "message": (
                        "Solo se pueden modificar "
                        "garantías pendientes."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ========================================================
        # Solo se permite modificar el motivo
        # ========================================================

        campos_permitidos = {
            "motivo"
        }

        campos_recibidos = set(
            request.data.keys()
        )

        campos_no_permitidos = (
            campos_recibidos - campos_permitidos
        )

        if campos_no_permitidos:

            campo = next(
                iter(campos_no_permitidos)
            )

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

        # ========================================================
        # Validar motivo
        # ========================================================

        if "motivo" not in request.data:

            return Response(
                {
                    "success": False,
                    "message": (
                        "El campo 'motivo' "
                        "es obligatorio."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        motivo = request.data["motivo"]

        if not isinstance(motivo, str) or not motivo.strip():

            return Response(
                {
                    "success": False,
                    "message": (
                        "El motivo no puede estar vacío."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ========================================================
        # Actualizar
        # ========================================================

        garantia.motivo = motivo.strip()

        garantia.save(
            update_fields=[
                "motivo",
                "fecha_actualizacion"
            ]
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Garantía actualizada correctamente."
                ),
                "data": GarantiaSerializer(
                    garantia
                ).data
            },
            status=status.HTTP_200_OK
        )


class GarantiaAprobarView(APIView):

    permission_classes = [IsAdmin]

    # POST /api/garantias/<id>/aprobar/
    def post(self, request, id):

        serializer = AprobarGarantiaSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            garantia = aprobar_garantia(
                id,
                serializer.validated_data,
                request.user
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Garantía aprobada correctamente."
                    ),
                    "data": GarantiaSerializer(
                        garantia
                    ).data
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


class GarantiaRechazarView(APIView):

    permission_classes = [IsAdmin]

    # POST /api/garantias/<id>/rechazar/
    def post(self, request, id):

        serializer = RechazarGarantiaSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            garantia = rechazar_garantia(
                id,
                serializer.validated_data,
                request.user
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Garantía rechazada correctamente."
                    ),
                    "data": GarantiaSerializer(
                        garantia
                    ).data
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


class GarantiaFinalizarView(APIView):

    permission_classes = [IsAdmin]

    # POST /api/garantias/<id>/finalizar/
    def post(self, request, id):

        serializer = FinalizarGarantiaSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:

            garantia = finalizar_garantia(
                id,
                serializer.validated_data,
                request.user
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        "Garantía finalizada correctamente."
                    ),
                    "data": GarantiaSerializer(
                        garantia
                    ).data
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