from django.db import transaction, IntegrityError

from rest_framework import (
    viewsets,
    status
)

from rest_framework.response import Response

from rest_framework.permissions import (
    IsAuthenticated
)

from rest_framework.decorators import action

from rest_framework.pagination import PageNumberPagination

from .models import Variante
from .serializers import VarianteSerializer

from usuarios.permissions import IsAdmin

from bitacora.services import registrar_bitacora


class VariantePagination(PageNumberPagination):

    page_size = 50

    page_size_query_param = "page_size"

    max_page_size = 200


class VarianteViewSet(
    viewsets.ModelViewSet
):

    queryset = Variante.objects.filter(
        activo=True
    )

    serializer_class = VarianteSerializer

    pagination_class = VariantePagination

    # ----------------------------------------------------------
    # SIN DELETE: el ciclo de vida se maneja con
    # activar/desactivar, no con el método HTTP DELETE.
    # ----------------------------------------------------------

    http_method_names = [
        "get",
        "post",
        "put",
        "patch",
        "head",
        "options"
    ]


    # ==========================================================
    # QUERYSET
    # ==========================================================

    def get_queryset(self):

        # ------------------------------------------------------
        # PARA MODIFICAR, REACTIVAR O DESACTIVAR
        # ------------------------------------------------------

        if self.action in [
            "update",
            "partial_update",
            "activar",
            "desactivar"
        ]:

            return Variante.objects.all()

        # ------------------------------------------------------
        # CONSULTAS NORMALES
        # ------------------------------------------------------

        queryset = Variante.objects.filter(
            activo=True
        )

        # ------------------------------------------------------
        # FILTRO OPCIONAL ?producto=<UUID>
        # (solo aplica al listado)
        # ------------------------------------------------------

        if self.action == "list":

            producto_id = self.request.query_params.get(
                "producto"
            )

            if producto_id:

                queryset = queryset.filter(
                    producto_id=producto_id
                )

        return queryset.order_by(
            "nombre",
            "id"
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

    def create(
        self,
        request,
        *args,
        **kwargs
    ):

        serializer = self.get_serializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(

                {
                    "success": False,

                    "message": (
                        "No se pudo registrar "
                        "la variante."
                    ),

                    "data": serializer.errors
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            with transaction.atomic():

                variante = serializer.save()

                registrar_bitacora(

                    usuario=request.user,

                    modulo="Variantes",

                    accion="CREAR_VARIANTE",

                    descripcion=(

                        f"Variante '{variante.nombre}' "

                        f"del producto "

                        f"'{variante.producto.nombre}' "

                        f"creada correctamente por "

                        f"{request.user.nombre} "

                        f"{request.user.apellido}."
                    )
                )

        except IntegrityError:

            return Response(

                {
                    "success": False,

                    "message": (
                        "Ya existe una variante con "
                        "este SKU o código de barras."
                    ),

                    "data": None
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(

            {
                "success": True,

                "message": (
                    "Variante registrada "
                    "correctamente."
                ),

                "data": VarianteSerializer(
                    variante
                ).data
            },

            status=status.HTTP_201_CREATED
        )


    # ==========================================================
    # MODIFICAR VARIANTE
    # (el estado 'activo' ya no puede cambiar aquí: lo
    # bloquea el serializer y se administra en activar/
    # desactivar)
    # ==========================================================

    def perform_update(
        self,
        serializer
    ):

        with transaction.atomic():

            variante = serializer.save()

            registrar_bitacora(

                usuario=self.request.user,

                modulo="Variantes",

                accion="MODIFICAR_VARIANTE",

                descripcion=(

                    f"Variante '{variante.nombre}' "

                    f"del producto "

                    f"'{variante.producto.nombre}' "

                    f"modificada correctamente por "

                    f"{self.request.user.nombre} "

                    f"{self.request.user.apellido}."
                )
            )


    # ==========================================================
    # ACTIVAR VARIANTE
    # ==========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="activar"
    )
    def activar(
        self,
        request,
        pk=None
    ):

        variante = self.get_object()

        if variante.activo:

            return Response(

                {
                    "success": False,

                    "message": (
                        "La variante ya está activa."
                    ),

                    "data": None
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        if not variante.producto.activo:

            return Response(

                {
                    "success": False,

                    "message": (
                        "No se puede activar la variante "
                        "porque su producto está inactivo."
                    ),

                    "data": None
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            variante.activo = True

            variante.save(
                update_fields=[
                    "activo",
                    "fecha_actualizacion"
                ]
            )

            registrar_bitacora(

                usuario=request.user,

                modulo="Variantes",

                accion="ACTIVAR_VARIANTE",

                descripcion=(

                    f"Variante '{variante.nombre}' "

                    f"del producto "

                    f"'{variante.producto.nombre}' "

                    f"activada correctamente por "

                    f"{request.user.nombre} "

                    f"{request.user.apellido}."
                )
            )

        return Response(

            {
                "success": True,

                "message": (
                    "Variante activada "
                    "correctamente."
                ),

                "data": VarianteSerializer(
                    variante
                ).data
            },

            status=status.HTTP_200_OK
        )


    # ==========================================================
    # DESACTIVAR VARIANTE
    # ==========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="desactivar"
    )
    def desactivar(
        self,
        request,
        pk=None
    ):

        variante = self.get_object()

        if not variante.activo:

            return Response(

                {
                    "success": False,

                    "message": (
                        "La variante ya está inactiva."
                    ),

                    "data": None
                },

                status=status.HTTP_400_BAD_REQUEST
            )

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