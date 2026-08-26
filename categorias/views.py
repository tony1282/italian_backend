from rest_framework import viewsets, status
from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated

from .models import Categoria
from .serializers import CategoriaSerializer

from bitacora.services import registrar_bitacora


class CategoriaViewSet(viewsets.ModelViewSet):

    queryset = Categoria.objects.filter(
        activo=True
    )

    serializer_class = CategoriaSerializer

    permission_classes = [
        IsAuthenticated
    ]

    # ============================================================
    # CREAR CATEGORÍA
    # ============================================================

    def perform_create(self, serializer):

        categoria = serializer.save()

        registrar_bitacora(

            usuario=self.request.user,

            modulo="Categorias",

            accion="CREAR_CATEGORIA",

            descripcion=(
                f"Categoría '{categoria.nombre}' "
                f"creada por "
                f"{self.request.user.nombre} "
                f"{self.request.user.apellido}. "
                f"Descripción: "
                f"{categoria.descripcion or 'Sin descripción'}."
            )

        )

    # ============================================================
    # ACTUALIZAR CATEGORÍA
    # ============================================================

    def perform_update(self, serializer):

        categoria = serializer.save()

        registrar_bitacora(

            usuario=self.request.user,

            modulo="Categorias",

            accion="ACTUALIZAR_CATEGORIA",

            descripcion=(
                f"Categoría '{categoria.nombre}' "
                f"actualizada por "
                f"{self.request.user.nombre} "
                f"{self.request.user.apellido}. "
                f"Descripción: "
                f"{categoria.descripcion or 'Sin descripción'}."
            )

        )

    # ============================================================
    # DESACTIVAR CATEGORÍA
    # ============================================================

    def destroy(
        self,
        request,
        *args,
        **kwargs
    ):

        categoria = self.get_object()

        categoria.activo = False

        categoria.save(
            update_fields=[
                "activo"
            ]
        )

        registrar_bitacora(

            usuario=request.user,

            modulo="Categorias",

            accion="DESACTIVAR_CATEGORIA",

            descripcion=(
                f"Categoría '{categoria.nombre}' "
                f"desactivada por "
                f"{request.user.nombre} "
                f"{request.user.apellido}."
            )

        )

        return Response(

            {
                "mensaje": (
                    "Categoría desactivada correctamente"
                )
            },

            status=status.HTTP_200_OK
        )