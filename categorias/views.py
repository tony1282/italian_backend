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

from usuarios.permissions import IsAdmin

from .models import Categoria

from .serializers import (
    CategoriaSerializer
)

from bitacora.services import (
    registrar_bitacora
)


class CategoriaViewSet(
    viewsets.ModelViewSet
):

    queryset = Categoria.objects.all()

    serializer_class = CategoriaSerializer

    http_method_names = [
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options"
    ]

    # ==========================================================
    # QUERYSET
    # ==========================================================

    def get_queryset(self):

        # ------------------------------------------------------
        # ADMIN
        # Puede consultar categorías activas e inactivas.
        # ------------------------------------------------------

        if (
            self.request.user.is_authenticated
            and self.request.user.rol in (0, 1)
            and self.request.user.activo
        ):

            return Categoria.objects.all().order_by(
                "nombre",
                "id"
            )

        # ------------------------------------------------------
        # EMPLEADO
        # Solo categorías activas.
        # ------------------------------------------------------

        return Categoria.objects.filter(
            activo=True
        ).order_by(
            "nombre",
            "id"
        )

    # ==========================================================
    # PERMISOS
    # ==========================================================

    def get_permissions(self):

        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "activar",
            "desactivar"
        ]:

            return [
                IsAuthenticated(),
                IsAdmin()
            ]

        return [
            IsAuthenticated()
        ]

    # ==========================================================
    # CREAR CATEGORÍA
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
                        "la categoría."
                    ),
                    "data": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            with transaction.atomic():

                categoria = serializer.save()

                registrar_bitacora(

                    usuario=request.user,

                    modulo="Categorias",

                    accion="CREAR_CATEGORIA",

                    descripcion=(
                        f"Categoría '{categoria.nombre}' "
                        f"creada por "
                        f"{request.user.nombre} "
                        f"{request.user.apellido}. "
                        f"Descripción: "
                        f"{categoria.descripcion or 'Sin descripción'}."
                    )
                )

        except IntegrityError:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Ya existe una categoría "
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
                    "Categoría registrada "
                    "correctamente."
                ),
                "data": CategoriaSerializer(
                    categoria
                ).data
            },
            status=status.HTTP_201_CREATED
        )

    # ==========================================================
    # ACTUALIZAR CATEGORÍA
    # ==========================================================

    def update(
        self,
        request,
        *args,
        **kwargs
    ):

        categoria = self.get_object()

        serializer = self.get_serializer(
            categoria,
            data=request.data,
            partial=False
        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "message": (
                        "No se pudo actualizar "
                        "la categoría."
                    ),
                    "data": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            with transaction.atomic():

                categoria = serializer.save()

                registrar_bitacora(

                    usuario=request.user,

                    modulo="Categorias",

                    accion="ACTUALIZAR_CATEGORIA",

                    descripcion=(
                        f"Categoría '{categoria.nombre}' "
                        f"actualizada por "
                        f"{request.user.nombre} "
                        f"{request.user.apellido}. "
                        f"Descripción: "
                        f"{categoria.descripcion or 'Sin descripción'}."
                    )
                )

        except IntegrityError:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Ya existe una categoría "
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
                    "Categoría actualizada "
                    "correctamente."
                ),
                "data": CategoriaSerializer(
                    categoria
                ).data
            },
            status=status.HTTP_200_OK
        )

    # ==========================================================
    # PATCH
    # ==========================================================

    def partial_update(
        self,
        request,
        *args,
        **kwargs
    ):

        categoria = self.get_object()

        serializer = self.get_serializer(
            categoria,
            data=request.data,
            partial=True
        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "message": (
                        "No se pudo actualizar "
                        "la categoría."
                    ),
                    "data": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            with transaction.atomic():

                categoria = serializer.save()

                registrar_bitacora(

                    usuario=request.user,

                    modulo="Categorias",

                    accion="ACTUALIZAR_CATEGORIA",

                    descripcion=(
                        f"Categoría '{categoria.nombre}' "
                        f"actualizada por "
                        f"{request.user.nombre} "
                        f"{request.user.apellido}."
                    )
                )

        except IntegrityError:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Ya existe una categoría "
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
                    "Categoría actualizada "
                    "correctamente."
                ),
                "data": CategoriaSerializer(
                    categoria
                ).data
            },
            status=status.HTTP_200_OK
        )

    # ==========================================================
    # ACTIVAR CATEGORÍA
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

        categoria = self.get_object()

        if categoria.activo:

            return Response(
                {
                    "success": False,
                    "message": (
                        "La categoría ya está activa."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            categoria.activo = True

            categoria.save(
                update_fields=[
                    "activo",
                    "fecha_actualizacion"
                ]
            )

            registrar_bitacora(

                usuario=request.user,

                modulo="Categorias",

                accion="ACTIVAR_CATEGORIA",

                descripcion=(
                    f"Categoría '{categoria.nombre}' "
                    f"activada correctamente por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}."
                )
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Categoría activada "
                    "correctamente."
                ),
                "data": CategoriaSerializer(
                    categoria
                ).data
            },
            status=status.HTTP_200_OK
        )

    # ==========================================================
    # DESACTIVAR CATEGORÍA
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

        categoria = self.get_object()

        if not categoria.activo:

            return Response(
                {
                    "success": False,
                    "message": (
                        "La categoría ya está inactiva."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ------------------------------------------------------
        # NO DESACTIVAR SI TIENE PRODUCTOS ACTIVOS
        # ------------------------------------------------------

        if categoria.productos.filter(
            activo=True
        ).exists():

            return Response(
                {
                    "success": False,
                    "message": (
                        "No se puede desactivar "
                        "la categoría porque tiene "
                        "productos activos."
                    ),
                    "data": None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            categoria.activo = False

            categoria.save(
                update_fields=[
                    "activo",
                    "fecha_actualizacion"
                ]
            )

            registrar_bitacora(

                usuario=request.user,

                modulo="Categorias",

                accion="DESACTIVAR_CATEGORIA",

                descripcion=(
                    f"Categoría '{categoria.nombre}' "
                    f"desactivada correctamente por "
                    f"{request.user.nombre} "
                    f"{request.user.apellido}."
                )
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Categoría desactivada "
                    "correctamente."
                ),
                "data": None
            },
            status=status.HTTP_200_OK
        )

    # ==========================================================
    # DELETE
    # ==========================================================
    # DELETE conserva la desactivación lógica.
    # ==========================================================

    def destroy(
        self,
        request,
        *args,
        **kwargs
    ):

        return self.desactivar(
            request,
            *args,
            **kwargs
        )