from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Variante
from .serializers import VarianteSerializer

from rest_framework.decorators import action

from bitacora.services import registrar_bitacora


class VarianteViewSet(viewsets.ModelViewSet):

    queryset = Variante.objects.filter(
        activo=True
    )

    serializer_class = VarianteSerializer

    permission_classes = [
        IsAuthenticated
    ]


    # ==========================================================
    # CREAR VARIANTE
    # ==========================================================

    def perform_create(self, serializer):

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
    # MODIFICAR VARIANTE
    # ==========================================================

    def perform_update(self, serializer):

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
    # DESACTIVAR VARIANTE
    # ==========================================================

    def destroy(
        self,
        request,
        *args,
        **kwargs
    ):

        variante = self.get_object()

        variante.activo = False
        variante.save()

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
                    "Variante desactivada correctamente."
                )
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
                serializer.data
            )

        except Variante.DoesNotExist:

            return Response(

                {
                    "success": False,

                    "message": (
                        "No existe una variante "
                        "con ese codigo"
                    )
                },

                status=status.HTTP_404_NOT_FOUND
            )