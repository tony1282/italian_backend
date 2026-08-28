from django.db import transaction, IntegrityError

from rest_framework import (
    viewsets,
    status
)

from rest_framework.response import Response

from rest_framework.permissions import (
    IsAuthenticated
)

from rest_framework.pagination import PageNumberPagination

from .models import Producto

from .serializers import (
    ProductoSerializer
)

from usuarios.permissions import (
    IsAdmin
)

from bitacora.services import (
    registrar_bitacora
)


class ProductoPagination(PageNumberPagination):

    page_size = 50

    max_page_size = 200


class ProductoViewSet(
    viewsets.ModelViewSet
):

    queryset = Producto.objects.filter(
        activo=True
    )

    serializer_class = ProductoSerializer

    pagination_class = ProductoPagination


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

            return Producto.objects.all()

        # ------------------------------------------------------
        # CONSULTAS NORMALES
        # ------------------------------------------------------

        return Producto.objects.filter(
            activo=True
        )


    # ==========================================================
    # PERMISOS
    # ==========================================================

    def get_permissions(
        self
    ):

        if self.action in [
            "list",
            "retrieve"
        ]:

            return [
                IsAuthenticated()
            ]

        return [
            IsAuthenticated(),
            IsAdmin()
        ]


    # ==========================================================
    # CREAR PRODUCTO
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
                        "el producto."
                    ),

                    "data": serializer.errors
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            with transaction.atomic():

                producto = serializer.save()

                registrar_bitacora(

                    usuario=request.user,

                    modulo="Productos",

                    accion="CREAR_PRODUCTO",

                    descripcion=(

                        f"Producto '{producto.nombre}' "

                        f"creado correctamente por "

                        f"{request.user.nombre} "

                        f"{request.user.apellido}."
                    )
                )

        except IntegrityError:

            return Response(

                {
                    "success": False,

                    "message": (
                        "Ya existe un producto "
                        "con este nombre."
                    ),

                    "data": None
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(

            {
                "success": True,

                "message": (
                    "Producto registrado "
                    "correctamente."
                ),

                "data": ProductoSerializer(
                    producto
                ).data
            },

            status=status.HTTP_201_CREATED
        )


    # ==========================================================
    # MODIFICAR / ACTIVAR / DESACTIVAR PRODUCTO
    # ==========================================================

    def perform_update(
        self,
        serializer
    ):

        producto_anterior = self.get_object()

        activo_anterior = producto_anterior.activo

        with transaction.atomic():

            producto = serializer.save()

            # --------------------------------------------------
            # ACTIVAR
            # --------------------------------------------------

            if (
                activo_anterior is False
                and producto.activo is True
            ):

                accion = "ACTIVAR_PRODUCTO"

                descripcion = (

                    f"Producto '{producto.nombre}' "

                    f"activado correctamente por "

                    f"{self.request.user.nombre} "

                    f"{self.request.user.apellido}."
                )

            # --------------------------------------------------
            # DESACTIVAR
            # --------------------------------------------------

            elif (
                activo_anterior is True
                and producto.activo is False
            ):

                accion = "DESACTIVAR_PRODUCTO"

                descripcion = (

                    f"Producto '{producto.nombre}' "

                    f"desactivado correctamente por "

                    f"{self.request.user.nombre} "

                    f"{self.request.user.apellido}."
                )

            # --------------------------------------------------
            # MODIFICAR
            # --------------------------------------------------

            else:

                accion = "MODIFICAR_PRODUCTO"

                descripcion = (

                    f"Producto '{producto.nombre}' "

                    f"modificado correctamente por "

                    f"{self.request.user.nombre} "

                    f"{self.request.user.apellido}."
                )

            registrar_bitacora(

                usuario=self.request.user,

                modulo="Productos",

                accion=accion,

                descripcion=descripcion

            )


    # ==========================================================
    # DESACTIVAR PRODUCTO
    # ==========================================================

    def destroy(
        self,
        request,
        *args,
        **kwargs
    ):

        producto = self.get_object()

        # ------------------------------------------------------
        # NO DESACTIVAR SI TIENE VARIANTES ACTIVAS
        # ------------------------------------------------------

        if producto.variantes.filter(
            activo=True
        ).exists():

            return Response(

                {
                    "success": False,

                    "message": (
                        "No se puede desactivar "
                        "el producto porque tiene "
                        "variantes activas."
                    ),

                    "data": None
                },

                status=status.HTTP_400_BAD_REQUEST
            )

        # ------------------------------------------------------
        # DESACTIVACIÓN LÓGICA
        # ------------------------------------------------------

        with transaction.atomic():

            producto.activo = False

            producto.save(
                update_fields=[
                    "activo",
                    "fecha_actualizacion"
                ]
            )

            registrar_bitacora(

                usuario=request.user,

                modulo="Productos",

                accion="DESACTIVAR_PRODUCTO",

                descripcion=(

                    f"Producto '{producto.nombre}' "

                    f"desactivado correctamente por "

                    f"{request.user.nombre} "

                    f"{request.user.apellido}."
                )
            )

        return Response(

            {
                "success": True,

                "message": (
                    "Producto desactivado "
                    "correctamente."
                ),

                "data": None
            },

            status=status.HTTP_200_OK
        )