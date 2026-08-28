from django.db import transaction

from rest_framework import (
    viewsets,
    status
)

from rest_framework.response import Response

from rest_framework.permissions import (
    IsAuthenticated
)

from .models import Variante
from .serializers import VarianteSerializer

from rest_framework.decorators import action

from usuarios.permissions import IsAdmin

from bitacora.services import registrar_bitacora


class VarianteViewSet(
    viewsets.ModelViewSet
):

    queryset = Variante.objects.filter(
        activo=True
    )

    serializer_class = VarianteSerializer


    # ==========================================================
    # QUERYSET
    # ==========================================================

    def get_queryset(self):

        # ------------------------------------------------------
        # PARA MODIFICAR O REACTIVAR
        # ------------------------------------------------------

        if self.action in [
            "update",
            "partial_update"
        ]:

            return Variante.objects.all()

        # ------------------------------------------------------
        # CONSULTAS NORMALES
        # ------------------------------------------------------

        return Variante.objects.filter(
            activo=True
        )


    # ==========================================================
    # PERMISOS
    # ==========================================================

    def get_permissions(self):

        if self.action in [
            "list",
            "retrieve",
            "buscar_por_codigo"
        ]:

            return [
                IsAuthenticated()
            ]

        return [
            IsAuthenticated(),
            IsAdmin()
        ]


    # ==========================================================
    # CREAR VARIANTE
    # ==========================================================

    def perform_create(
        self,
        serializer
    ):

        with transaction.atomic():

            variante = serializer.save()

            registrar_bitacora(

                usuario=self.request.user,

                modulo="Variantes",

                accion="CREAR_VARIANTE",

                descripcion=(
                    f"Variante '{variante.nombre}' "
                    f"del producto "
                    f"'{variante.producto.nombre}' "
                    f"creada correctamente por "
                    f"{self.request.user.nombre} "
                    f"{self.request.user.apellido}."
                )

            )


    # ==========================================================
    # MODIFICAR / ACTIVAR / DESACTIVAR VARIANTE
    # ==========================================================

    def perform_update(
        self,
        serializer
    ):

        variante_anterior = self.get_object()

        activo_anterior = variante_anterior.activo

        with transaction.atomic():

            variante = serializer.save()

            # --------------------------------------------------
            # ACTIVAR
            # --------------------------------------------------

            if (
                activo_anterior is False
                and variante.activo is True
            ):

                accion = "ACTIVAR_VARIANTE"

                descripcion = (
                    f"Variante '{variante.nombre}' "
                    f"del producto "
                    f"'{variante.producto.nombre}' "
                    f"activada correctamente por "
                    f"{self.request.user.nombre} "
                    f"{self.request.user.apellido}."
                )

            # --------------------------------------------------
            # DESACTIVAR
            # --------------------------------------------------

            elif (
                activo_anterior is True
                and variante.activo is False
            ):

                accion = "DESACTIVAR_VARIANTE"

                descripcion = (
                    f"Variante '{variante.nombre}' "
                    f"del producto "
                    f"'{variante.producto.nombre}' "
                    f"desactivada correctamente por "
                    f"{self.request.user.nombre} "
                    f"{self.request.user.apellido}."
                )

            # --------------------------------------------------
            # MODIFICAR
            # --------------------------------------------------

            else:

                accion = "MODIFICAR_VARIANTE"

                descripcion = (
                    f"Variante '{variante.nombre}' "
                    f"del producto "
                    f"'{variante.producto.nombre}' "
                    f"modificada correctamente por "
                    f"{self.request.user.nombre} "
                    f"{self.request.user.apellido}."
                )

            registrar_bitacora(

                usuario=self.request.user,

                modulo="Variantes",

                accion=accion,

                descripcion=descripcion

            )


    # ==========================================================
    # DESACTIVAR VARIANTE
    # ==========================================================

    def destroy(
        self,
        request,
        *args,
        **kwargs
    ):

        variante = self.get_object()

        with transaction.atomic():

            variante.activo = False

            variante.save(
                update_fields=[
                    "activo",
                    "fecha_actualizacion"
                ]
            )

            registrar_bitacora(

                usuario=request.user,

                modulo="Variantes",

                accion="DESACTIVAR_VARIANTE",

                descripcion=(
                    f"Variante '{variante.nombre}' "
                    f"del producto "
                    f"'{variante.producto.nombre}' "
                    f"desactivada correctamente por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}."
                )

            )

        return Response(

            {
                "success": True,

                "message": (
                    "Variante desactivada "
                    "correctamente."
                ),

                "data": None
            },

            status=status.HTTP_200_OK
        )


    # ==========================================================
    # BUSCAR VARIANTE POR CÓDIGO DE BARRAS
    # ==========================================================

    @action(
        detail=False,
        methods=["get"],
        url_path=r"codigo/(?P<codigo>[^/.]+)"
    )
    def buscar_por_codigo(
        self,
        request,
        codigo=None
    ):

        try:

            variante = Variante.objects.get(

                codigo_barras=codigo,

                activo=True

            )

            serializer = self.get_serializer(
                variante
            )

            return Response(

                {
                    "success": True,

                    "message": (
                        "Variante encontrada."
                    ),

                    "data": serializer.data
                },

                status=status.HTTP_200_OK
            )

        except Variante.DoesNotExist:

            return Response(

                {
                    "success": False,

                    "message": (
                        "No existe una variante "
                        "con ese código."
                    ),

                    "data": None
                },

                status=status.HTTP_404_NOT_FOUND
            )