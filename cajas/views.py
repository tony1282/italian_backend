from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError, transaction

from usuarios.permissions import IsAdmin

from .models import Caja
from .serializers import CajaSerializer

from bitacora.services import registrar_bitacora


class CajaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):

    queryset = Caja.objects.all().order_by(
        "nombre",
        "id"
    )

    serializer_class = CajaSerializer

    def get_permissions(self):

        if self.action in [
            "create",
            "update",
            "partial_update",
            "activar",
            "desactivar",
        ]:
            return [
                IsAuthenticated(),
                IsAdmin()
            ]

        return [
            IsAuthenticated()
        ]

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

    def retrieve(self, request, pk=None):

        caja = self.get_object()

        serializer = self.get_serializer(
            caja
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def create(self, request):

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

        try:

            with transaction.atomic():

                caja = serializer.save()

                registrar_bitacora(
                    usuario=request.user,
                    modulo="Caja",
                    accion="CREAR_CAJA",
                    descripcion=(
                        f"Caja '{caja.nombre}' creada correctamente por "
                        f"{request.user.nombre} {request.user.apellido}."
                    )
                )

        except IntegrityError:

            return Response(
                {
                    "success": False,
                    "message": "Ya existe una caja con ese nombre."
                },
                status=status.HTTP_409_CONFLICT
            )

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

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop(
            "partial",
            False
        )

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            with transaction.atomic():

                caja = serializer.save()

                registrar_bitacora(
                    usuario=request.user,
                    modulo="Caja",
                    accion="ACTUALIZAR_CAJA",
                    descripcion=(
                        f"Caja '{caja.nombre}' actualizada correctamente por "
                        f"{request.user.nombre} {request.user.apellido}."
                    )
                )

        except IntegrityError:

            return Response(
                {
                    "success": False,
                    "message": "Ya existe una caja con ese nombre."
                },
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            {
                "success": True,
                "message": "Caja actualizada correctamente.",
                "data": self.get_serializer(caja).data
            },
            status=status.HTTP_200_OK
        )

    @action(
        detail=False,
        methods=["get"]
    )
    def activas(self, request):

        cajas = Caja.objects.filter(
            activa=True
        ).order_by(
            "nombre",
            "id"
        )

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

    @action(
        detail=True,
        methods=["post"]
    )
    def activar(self, request, pk=None):

        caja = self.get_object()

        if caja.activa:

            return Response(
                {
                    "success": False,
                    "message": "La caja ya está activa."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            caja.activa = True

            caja.save(
                update_fields=[
                    "activa",
                    "fecha_actualizacion"
                ]
            )

            registrar_bitacora(
                usuario=request.user,
                modulo="Caja",
                accion="ACTIVAR_CAJA",
                descripcion=(
                    f"Caja '{caja.nombre}' activada correctamente por "
                    f"{request.user.nombre} {request.user.apellido}."
                )
            )

        return Response(
            {
                "success": True,
                "message": "Caja activada correctamente."
            },
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["post"]
    )
    def desactivar(self, request, pk=None):

        caja = self.get_object()

        if not caja.activa:

            return Response(
                {
                    "success": False,
                    "message": "La caja ya está inactiva."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if caja.estado == Caja.ESTADO_ABIERTA:

            return Response(
                {
                    "success": False,
                    "message": (
                        "No se puede desactivar la caja porque "
                        "tiene un corte abierto."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            caja.activa = False

            caja.save(
                update_fields=[
                    "activa",
                    "fecha_actualizacion"
                ]
            )

            registrar_bitacora(
                usuario=request.user,
                modulo="Caja",
                accion="DESACTIVAR_CAJA",
                descripcion=(
                    f"Caja '{caja.nombre}' desactivada correctamente por "
                    f"{request.user.nombre} {request.user.apellido}."
                )
            )

        return Response(
            {
                "success": True,
                "message": "Caja desactivada correctamente."
            },
            status=status.HTTP_200_OK
        )